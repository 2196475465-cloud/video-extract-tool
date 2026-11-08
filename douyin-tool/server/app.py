"""去水印工具后端：零第三方依赖，`python app.py` 直接跑。

接口一览
    GET  /api/health          健康检查（监控用）
    GET  /api/config          小程序读取的公开配置（广告位、次数限制、公告）
    POST /api/parse           {"url": "分享文案或链接"} → 作品信息（含签名下载链接）
    GET  /api/dl              下载/预览代理（带签名，防止被刷）
    POST /api/feedback        意见反馈
    GET  /admin               运营后台（?token=后台密码）
"""

from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
import socket
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.admin import ADMIN_HTML  # noqa: E402
from core.browser import BrowserPool  # noqa: E402
from core.db import open_store  # noqa: E402
from core.douyin import DouyinParser, ParseError  # noqa: E402
from core.settings import Settings  # noqa: E402

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DATA_PATH = os.path.join(BASE_DIR, "data", "data.db")
WEB_DIR = os.path.normpath(os.path.join(BASE_DIR, "web"))

settings = Settings(CONFIG_PATH)
store = open_store(DATA_PATH)
pool = BrowserPool(settings.section("parse"))
parser = DouyinParser(settings, store, pool)

_RATE_LOCK = threading.Lock()
_RATE: dict[str, list] = {}


def rate_ok(ip: str, limit: int = 40, window: int = 60) -> bool:
    now = time.time()
    with _RATE_LOCK:
        bucket = _RATE.setdefault(ip, [0, now])
        if now - bucket[1] > window:
            bucket[0], bucket[1] = 0, now
        bucket[0] += 1
        return bucket[0] <= limit


def sign_payload(secret: str, kind: str, aweme_id: str, index: str, expire: int) -> str:
    msg = f"{kind}|{aweme_id}|{index}|{expire}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:20]


def build_download_url(kind: str, aweme_id: str, index: int = 0, ttl: int = 7200,
                       base: str = "") -> str:
    secret = settings.get("server", "secret", default="")
    expire = int(time.time()) + ttl
    sig = sign_payload(secret, kind, aweme_id, str(index), expire)
    base = (base or settings.get("server", "public_base", default="") or "").rstrip("/")
    query = urllib.parse.urlencode({"k": kind, "id": aweme_id, "i": index, "e": expire, "s": sig})
    return f"{base}/api/dl?{query}"


def attach_links(item: dict, base: str = "") -> dict:
    aid = item.get("id", "")
    out = dict(item)
    out["download"] = {
        "video": build_download_url("video", aid, base=base) if item.get("video", {}).get("url") else "",
        "cover": build_download_url("cover", aid, base=base) if item.get("cover") else "",
        "music": build_download_url("music", aid, base=base) if item.get("music", {}).get("url") else "",
        "images": [build_download_url("image", aid, i, base=base) for i, _ in enumerate(item.get("images") or [])],
    }
    return out


def safe_filename(title: str, ext: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|\r\n#@]+", " ", title or "").strip()
    name = re.sub(r"\s+", " ", name)[:48] or "douyin"
    return f"{name}{ext}"


def guess_ext(url: str, default: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext in (".mp4", ".jpeg", ".jpg", ".png", ".webp", ".mp3", ".m4a"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return default


class Handler(BaseHTTPRequestHandler):
    server_version = "DouyinTool/1.0"
    protocol_version = "HTTP/1.1"

    # -- 基础工具 -------------------------------------------------------- #
    def log_message(self, fmt, *args):  # 静音默认日志
        if os.environ.get("DEBUG"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8",
              extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Admin-Token")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, payload: dict):
        self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")) or {}
        except Exception:
            return {}

    @property
    def ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For")
        if fwd:
            return fwd.split(",")[0].strip()
        return self.client_address[0]

    def base_url(self) -> str:
        """没配 public_base 时用当前请求域名兜底，方便本地联调。"""
        configured = (settings.get("server", "public_base", default="") or "").rstrip("/")
        if configured:
            return configured
        proto = self.headers.get("X-Forwarded-Proto") or "http"
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "127.0.0.1:8000"
        return f"{proto}://{host}"

    def _admin_ok(self, query: dict) -> bool:
        token = (query.get("token") or [""])[0] or self.headers.get("X-Admin-Token", "")
        expect = settings.get("server", "admin_token", default="")
        return bool(expect) and hmac.compare_digest(str(token), str(expect))

    # -- 路由 ------------------------------------------------------------ #
    def do_OPTIONS(self):  # noqa: N802
        self._send(204, b"")

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/api/health":
                self._json(200, {"ok": True, "browser": pool.alive,
                                 "uptime": int(time.time() - (pool.started_at or time.time()))})
            elif path == "/api/config":
                self._json(200, {"code": 0, "data": settings.public()})
            elif path == "/api/dl":
                self.handle_download(query)
            elif path == "/admin":
                self._send(200, ADMIN_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path.startswith("/admin/api/"):
                self.handle_admin_get(path, query)
            elif path in ("/", "/index.html"):
                self.serve_web("index.html")
            elif path.startswith("/web/"):
                self.serve_web(path[len("/web/"):])
            else:
                self._json(404, {"code": 404, "msg": "not found"})
        except BrokenPipeError:
            pass
        except Exception:
            traceback.print_exc()
            self._json(500, {"code": 500, "msg": "server error"})

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/api/parse":
                self.handle_parse()
            elif path == "/api/feedback":
                body = self._body()
                content = (body.get("content") or "").strip()
                if len(content) < 2:
                    self._json(400, {"code": 400, "msg": "说点什么再提交吧"})
                    return
                store.add_feedback(content, body.get("contact", ""), body.get("device", ""))
                self._json(200, {"code": 0, "msg": "已收到，谢谢反馈"})
            elif path.startswith("/admin/api/"):
                if not self._admin_ok(query) and not self._admin_ok({}):
                    self._json(401, {"code": 401, "msg": "后台密码不对"})
                    return
                self.handle_admin_post(path)
            else:
                self._json(404, {"code": 404, "msg": "not found"})
        except BrokenPipeError:
            pass
        except Exception:
            traceback.print_exc()
            self._json(500, {"code": 500, "msg": "server error"})

    # -- 业务 ------------------------------------------------------------ #
    def serve_web(self, rel: str):
        """托管网页版静态文件（手机 / 电脑浏览器打开即用）。"""
        rel = (rel or "index.html").lstrip("/")
        full = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            self._json(404, {"code": 404, "msg": "not found"})
            return
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as fp:
            data = fp.read()
        self._send(200, data, ctype, {"Cache-Control": "no-cache"})

    def handle_parse(self):
        if not rate_ok(self.ip):
            self._json(429, {"code": 429, "msg": "操作太频繁，歇一会儿再试"})
            return
        settings.reload_if_changed()
        body = self._body()
        text = body.get("url") or body.get("text") or ""
        device = (body.get("device") or "")[:64]
        if not pool.alive:
            try:
                pool.start()
            except Exception as exc:  # noqa: BLE001
                self._json(503, {"code": 503, "msg": f"解析服务启动失败：{exc}"})
                return
        try:
            item = parser.parse_text(text, device=device, ip=self.ip)
            self._json(200, {"code": 0, "data": attach_links(item, self.base_url())})
        except ParseError as exc:
            self._json(200, {"code": 1, "code_type": exc.code, "msg": exc.message})

    def handle_download(self, query: dict):
        kind = (query.get("k") or [""])[0]
        aweme_id = (query.get("id") or [""])[0]
        index = (query.get("i") or ["0"])[0]
        expire = (query.get("e") or ["0"])[0]
        sig = (query.get("s") or [""])[0]
        secret = settings.get("server", "secret", default="")

        if not (kind in ("video", "cover", "music", "image") and aweme_id.isdigit()):
            self._json(400, {"code": 400, "msg": "参数不对"})
            return
        if not sig or not hmac.compare_digest(sig, sign_payload(secret, kind, aweme_id, index, int(expire or 0))):
            self._json(403, {"code": 403, "msg": "下载链接无效，回小程序重新解析"})
            return
        if int(expire or 0) < time.time():
            self._json(403, {"code": 403, "msg": "下载链接过期了，回小程序重新解析"})
            return

        item = store.cache_get(aweme_id, 0)
        if not item:
            try:
                detail = pool.detail(aweme_id)
                from core.douyin import normalize
                item = normalize(detail)
                store.cache_put(aweme_id, item)
            except Exception:
                self._json(404, {"code": 404, "msg": "作品信息已过期，请重新解析"})
                return

        if kind == "video":
            url = item.get("video", {}).get("url", "")
            ext = ".mp4"
        elif kind == "cover":
            url = item.get("cover", "")
            ext = ".jpg"
        elif kind == "music":
            url = item.get("music", {}).get("url", "")
            ext = ".mp3"
        else:
            images = item.get("images") or []
            try:
                url = images[int(index)]
            except (ValueError, IndexError):
                url = ""
            ext = ".jpg"

        if not url:
            self._json(404, {"code": 404, "msg": "没有这个资源"})
            return

        try:
            upstream = parser.fetch_bytes(url)
        except Exception:
            self._json(502, {"code": 502, "msg": "下载失败，链接可能已过期，重新解析一次"})
            return

        length = upstream.headers.get("Content-Length")
        ctype = upstream.headers.get("Content-Type") or mimetypes.guess_type(url)[0] or "application/octet-stream"
        filename = safe_filename(item.get("title", ""), guess_ext(url, ext))

        attach = (query.get("d") or [""])[0] == "1"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if length:
            self.send_header("Content-Length", length)
        self.send_header(
            "Content-Disposition",
            f"{'attachment' if attach else 'inline'}; filename*=UTF-8''{urllib.parse.quote(filename)}",
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        try:
            while True:
                chunk = upstream.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            upstream.close()

    # -- 后台 ------------------------------------------------------------ #
    def handle_admin_get(self, path: str, query: dict):
        if not self._admin_ok(query) and not self._admin_ok({}):
            self._json(401, {"code": 401, "msg": "后台密码不对"})
            return
        if path == "/admin/api/overview":
            settings.reload_if_changed()
            self._json(200, {
                "code": 0,
                "data": {
                    "stats": store.stats(7),
                    "config": settings._data,  # noqa: SLF001 后台可见全部
                    "browser": {"alive": pool.alive, "workers": pool.workers_count,
                                "uptime": int(time.time() - (pool.started_at or time.time())),
                                "last_error": pool.last_error, "chrome": pool.chrome_path},
                    "feedback": store.feedback_list(30),
                },
            })
        elif path == "/admin/api/ping":
            self._json(200, {"code": 0})

    def handle_admin_post(self, path: str):
        body = self._body()
        if path == "/admin/api/config":
            updates = body.get("updates") or {}
            if not isinstance(updates, dict):
                self._json(400, {"code": 400, "msg": "格式不对"})
                return
            allowed = {"ads", "limits", "app", "server", "parse"}
            updates = {k: v for k, v in updates.items() if k in allowed}
            self._json(200, {"code": 0, "data": settings.patch(updates)})
        elif path == "/admin/api/test":
            text = body.get("url") or ""
            try:
                item = parser.parse_text(text, device="admin", ip="127.0.0.1")
                self._json(200, {"code": 0, "data": attach_links(item, self.base_url())})
            except ParseError as exc:
                self._json(200, {"code": 1, "msg": exc.message})
            except Exception as exc:  # noqa: BLE001
                self._json(200, {"code": 1, "msg": str(exc)[:200]})
        elif path == "/admin/api/restart":
            threading.Thread(target=pool.restart, daemon=True).start()
            self._json(200, {"code": 0, "msg": "正在重启浏览器，约 15 秒"})
        elif path == "/admin/api/cache":
            self._json(200, {"code": 0, "msg": f"已清理 {store.cache_clear()} 条缓存"})
        else:
            self._json(404, {"code": 404, "msg": "not found"})


def _landing() -> str:
    return """<!doctype html><meta charset="utf-8"><title>去水印工具后端</title>
<body style="font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:80px auto;padding:0 24px;line-height:1.8;color:#1a1a1a">
<h2>服务运行中</h2>
<p>这是一个给微信小程序用的抖音解析后端。</p>
<ul>
<li><code>GET /api/health</code> 健康检查</li>
<li><code>POST /api/parse</code> 解析接口</li>
<li><code>GET /admin</code> 运营后台</li>
</ul>
</body>"""


def main():
    host = settings.get("server", "host", default="0.0.0.0")
    port = int(settings.get("server", "port", default=8000))
    print("=" * 56)
    print(" 抖音去水印后端启动中…（首次加载浏览器约 15 秒）")
    print("=" * 56)
    try:
        pool.start()
        print(f"[ok] 浏览器就绪：{pool.chrome_path}")
        print(f"[ok] 预热标签页 {pool.workers_count} 个")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 浏览器启动失败：{exc}")
        print("       小程序仍可访问，解析会返回错误；修好 Chrome 后重启即可。")
    token = settings.get("server", "admin_token", default="")
    print(f"[ok] 后台地址：http://{host}:{port}/admin?token={token}")
    print(f"[ok] 接口地址：http://{host}:{port}/api/parse")
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n再见")
    finally:
        pool.stop()
        store.close()


if __name__ == "__main__":
    main()
