"""无头浏览器通道：用本机 Chrome 打开抖音页面，在页面内直接调用官方接口。

为什么需要它：抖音 2026 年起给 Web 接口加了 Argus 风控，纯服务端请求（即使
签名正确）会被 `Blocked by ArgusSecurityPlugin Uifid Not Found` 拦下。UIFID
只能由真实浏览器环境签发，所以这里复用一份真实 Chrome 环境：

1. 打开一个抖音视频页，等页面加载完（SDK 注入完成、UIFID 落盘）；
2. 之后在这个页面上下文里 fetch 作品详情接口，页面自己的 SDK 会自动签名；
3. 同一个标签页可以连续解析任意作品，单次约 0.3 ~ 0.5 秒。

实现只用标准库：CDP 走 WebSocket，自己做了最小帧编解码，不需要装 Playwright。
"""

from __future__ import annotations

import base64
import json
import os
import queue
import random
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- #
# 最小 WebSocket 客户端（仅用于本机 CDP，不对外）
# --------------------------------------------------------------------------- #


class _WS:
    def __init__(self, url: str, timeout: float = 30.0) -> None:
        if not url.startswith("ws://"):
            raise ValueError("only ws:// supported")
        hostport, path = url[5:].split("/", 1)
        path = "/" + path
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake closed")
            buf += chunk
        if b"101" not in buf.split(b"\r\n", 1)[0]:
            raise ConnectionError("websocket handshake failed")
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0
        self._lock = threading.Lock()

    def _send(self, obj: dict) -> None:
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        header = bytearray([0x81])
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def _read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _recv_message(self) -> dict:
        payload = b""
        while True:
            b1, b2 = self._read_exact(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            data = self._read_exact(length)
            if opcode == 0x9:  # ping
                continue
            if opcode == 0x8:  # close
                raise ConnectionError("closed by peer")
            payload += data
            if fin:
                return json.loads(payload.decode("utf-8", "ignore") or "{}")

    def call(self, method: str, params: dict | None = None, timeout: float = 40.0) -> dict:
        with self._lock:
            self._id += 1
            mid = self._id
            self._send({"id": mid, "method": method, "params": params or {}})
            deadline = time.time() + timeout
            while time.time() < deadline:
                msg = self._recv_message()
                if msg.get("id") == mid:
                    if "error" in msg:
                        raise RuntimeError(msg["error"].get("message", "cdp error"))
                    return msg.get("result", {})
            raise TimeoutError(f"cdp timeout: {method}")

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 页面内执行的作品详情请求
# --------------------------------------------------------------------------- #

_FETCH_JS = r"""
(async () => {
  const AID = '__AID__';
  const q = new URLSearchParams({
    device_platform: 'webapp', aid: '6383', channel: 'channel_pc_web',
    pc_client_type: '1', version_code: '290100', version_name: '29.1.0',
    cookie_enabled: 'true', screen_width: '1920', screen_height: '1080',
    browser_language: 'zh-CN', browser_platform: 'Win32', browser_name: 'Chrome',
    browser_version: '130.0.0.0', browser_online: 'true', engine_name: 'Blink',
    engine_version: '130.0.0.0', os_name: 'Windows', os_version: '10',
    cpu_core_num: '8', device_memory: '8', platform: 'PC', downlink: '10',
    effective_type: '4g', round_trip_time: '0', update_version_code: '170400',
    aweme_id: AID
  });
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  try {
    const r = await fetch(location.origin + '/aweme/v1/web/aweme/detail/?' + q.toString(),
                          { credentials: 'include', signal: ctrl.signal });
    const text = await r.text();
    clearTimeout(timer);
    if (!text) return JSON.stringify({ http: r.status, detail: null, empty: true });
    let body = {};
    try { body = JSON.parse(text); } catch (e) { return JSON.stringify({ http: r.status, raw: text.slice(0, 200) }); }
    return JSON.stringify({ http: r.status, status_code: body.status_code, detail: body.aweme_detail || null });
  } catch (e) {
    clearTimeout(timer);
    return JSON.stringify({ http: -1, error: String(e) });
  }
})()
"""


def _find_chrome(explicit: str = "") -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("CHROME_PATH")
    if env:
        candidates.append(env)
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""),
                     os.environ.get("LOCALAPPDATA", "")):
            if base:
                candidates.append(os.path.join(base, r"Google\Chrome\Application\chrome.exe"))
                candidates.append(os.path.join(base, r"Microsoft\Edge\Application\msedge.exe"))
    else:
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge",
        ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    found = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chrome")
    if found:
        return found
    raise RuntimeError(
        "没有找到 Chrome / Edge。请安装 Chrome，或在 config.json 的 parse.chrome_path 填绝对路径。"
    )


class _Worker:
    """一个标签页 + 一条 CDP 连接。"""

    def __init__(self, port: int, index: int) -> None:
        self.port = port
        self.index = index
        self.ws: _WS | None = None
        self.lock = threading.Lock()
        self.ready_until = 0.0

    def _new_tab(self, url: str) -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}",
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            target = json.loads(resp.read())
        if self.ws:
            self.ws.close()
        self.ws = _WS(target["webSocketDebuggerUrl"])
        self.ws.call("Runtime.enable")

    def _is_ready(self) -> bool:
        try:
            res = self.ws.call("Runtime.evaluate", {
                "expression": "document.readyState + '|' + location.host + '|' + (document.cookie.indexOf('UIFID') >= 0)",
                "returnByValue": True,
            })
            value = str(res.get("result", {}).get("value", ""))
            return value.startswith("complete|www.douyin.com|true")
        except Exception:
            return False

    def warm(self, seed_aid: str, timeout: float = 25.0) -> None:
        self._new_tab(f"https://www.douyin.com/video/{seed_aid}")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._is_ready():
                self.ready_until = time.time() + 600
                return
            time.sleep(0.5)
        raise TimeoutError("抖音页面加载超时（检查服务器能否访问 douyin.com）")

    def fetch(self, aid: str) -> dict:
        res = self.ws.call("Runtime.evaluate", {
            "expression": _FETCH_JS.replace("__AID__", aid),
            "awaitPromise": True,
            "returnByValue": True,
        }, timeout=30)
        if "exceptionDetails" in res:
            raise RuntimeError(str(res["exceptionDetails"])[:200])
        raw = res.get("result", {}).get("value")
        if not raw:
            raise RuntimeError("页面返回为空")
        return json.loads(raw)


class BrowserPool:
    """持有一次 Chrome 进程，内部若干标签页轮转解析。"""

    def __init__(self, config: dict) -> None:
        self.chrome_path = _find_chrome(config.get("chrome_path", ""))
        self.workers_count = max(1, int(config.get("workers", 2)))
        self.headless = bool(config.get("headless", True))
        self.seed_aid = str(config.get("seed_aid", "7420371100103707913"))
        self.port = 0
        self.proc: subprocess.Popen | None = None
        self.profile_dir = ""
        self._workers: queue.Queue[_Worker] = queue.Queue()
        self._start_lock = threading.Lock()
        self._restart_lock = threading.Lock()
        self.started_at = 0.0
        self.last_error = ""

    # -- lifecycle -------------------------------------------------------- #
    def _port(self) -> int:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def start(self) -> None:
        with self._start_lock:
            if self.proc and self.proc.poll() is None:
                return
            self.port = self._port()
            self.profile_dir = tempfile.mkdtemp(prefix="dy-browser-")
            args = [
                self.chrome_path,
                "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
                "--mute-audio", "--no-first-run", "--no-default-browser-check",
                "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={self.profile_dir}",
                "about:blank",
            ]
            if self.headless:
                args.insert(1, "--headless=new")
            self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.time() + 40
            while time.time() < deadline:
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=1).read()
                    break
                except Exception:
                    if self.proc.poll() is not None:
                        raise RuntimeError("Chrome 启动失败，请检查 chrome_path")
                    time.sleep(0.3)
            else:
                raise RuntimeError("Chrome 调试端口未就绪")
            self._workers = queue.Queue()
            for i in range(self.workers_count):
                worker = _Worker(self.port, i)
                worker.warm(self.seed_aid)
                self._workers.put(worker)
            self.started_at = time.time()

    def restart(self) -> None:
        with self._restart_lock:
            self.stop()
            self.start()

    def stop(self) -> None:
        try:
            while True:
                w = self._workers.get_nowait()
                if w.ws:
                    w.ws.close()
        except queue.Empty:
            pass
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=8)
            except Exception:
                self.proc.kill()
        self.proc = None
        if self.profile_dir:
            shutil.rmtree(self.profile_dir, ignore_errors=True)
            self.profile_dir = ""

    @property
    def alive(self) -> bool:
        return bool(self.proc and self.proc.poll() is None)

    # -- parsing ---------------------------------------------------------- #
    def detail(self, aid: str, retries: int = 2) -> dict:
        """返回 aweme_detail 字典。失败会重试并自动重新预热。"""
        if not self.alive:
            self.start()
        last = ""
        for attempt in range(retries + 1):
            worker = self._workers.get()
            try:
                with worker.lock:
                    if time.time() > worker.ready_until or not worker._is_ready():
                        worker.warm(self.seed_aid)
                    payload = worker.fetch(aid)
                http = payload.get("http")
                if http == -1:
                    raise RuntimeError(payload.get("error", "fetch failed"))
                if http == 403 or "Uifid" in str(payload.get("raw", "")):
                    raise _NeedRewarm("403 风控")
                if http != 200:
                    raise RuntimeError(f"HTTP {http}")
                detail = payload.get("detail")
                if not detail:
                    return {}
                return detail
            except _NeedRewarm:
                last = "风控拦截，已重新预热"
                try:
                    with worker.lock:
                        worker.ready_until = 0
                except Exception:
                    pass
            except Exception as exc:  # noqa: BLE001
                last = str(exc)[:200]
                try:
                    worker.ready_until = 0
                except Exception:
                    pass
            finally:
                self._workers.put(worker)
            time.sleep(0.4 * (attempt + 1))
        self.last_error = last
        raise RuntimeError(last or "解析失败")


class _NeedRewarm(Exception):
    pass
