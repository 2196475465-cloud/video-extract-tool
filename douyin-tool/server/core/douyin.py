"""抖音链接解析：提取链接 → 拿作品 ID → 浏览器通道取详情 → 归一化成前端要的结构。"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request

URL_RE = re.compile(r"https?://[^\s，。、；;\"'）)】\]]+", re.I)
ID_RE = re.compile(r"/(?:share/)?(video|note|slides)/(\d{15,25})")
SHORT_HOSTS = ("v.douyin.com", "v.kuaishou.com", "xhslink.com")

UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class ParseError(Exception):
    """带用户可读文案的解析失败。"""

    def __init__(self, message: str, code: str = "parse_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


# --------------------------------------------------------------------------- #
# 链接处理
# --------------------------------------------------------------------------- #


def extract_urls(text: str) -> list[str]:
    return [u.rstrip(".,;，。；") for u in URL_RE.findall(text or "")]


def resolve_short(url: str, timeout: float = 10.0) -> str:
    """短链跟随一次 302，拿到真正的落地地址。"""
    host = urllib.parse.urlparse(url).netloc.lower()
    if host not in SHORT_HOSTS:
        return url
    try:
        _OPENER.open(urllib.request.Request(url, headers={"User-Agent": UA_MOBILE}), timeout=timeout)
        return url
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location") or ""
        return location or url
    except Exception:
        return url


def pick_target(text: str) -> tuple[str, str]:
    """从一段分享文案里取出 (类型, 作品ID)。类型为 video / note / user。"""
    urls = extract_urls(text)
    if not urls and re.fullmatch(r"\d{15,25}", (text or "").strip()):
        return "video", text.strip()
    if not urls:
        raise ParseError("没有找到链接，请完整复制抖音的分享文案", "no_link")

    for url in urls[:3]:
        final = resolve_short(url)
        match = ID_RE.search(final)
        if match:
            return match.group(1), match.group(2)
        match = ID_RE.search(url)
        if match:
            return match.group(1), match.group(2)
        if "/share/user/" in final or "user/" in final:
            raise ParseError("这是主页链接，请复制单条视频的分享链接", "user_link")
        if "douyin.com" in final and "/video/" not in final:
            continue
    raise ParseError("没识别出作品 ID，可能链接已失效，换一条试试", "bad_link")


# --------------------------------------------------------------------------- #
# 归一化
# --------------------------------------------------------------------------- #


def _first(urls) -> str:
    if isinstance(urls, list):
        for u in urls:
            if isinstance(u, str) and u.startswith("http"):
                return u
    return ""


def _pick_play(video: dict) -> str:
    """优先 douyinvod 直连（无水印），退而取播放接口。"""
    for key in ("play_addr", "play_addr_265", "play_addr_h264"):
        url = _first((video.get(key) or {}).get("url_list"))
        if url:
            return url
    return ""


def normalize(detail: dict) -> dict:
    aweme_id = str(detail.get("aweme_id") or "")
    video = detail.get("video") or {}
    images_raw = detail.get("images") or []
    images = []
    for img in images_raw:
        url = _first(img.get("url_list")) if isinstance(img, dict) else ""
        if url:
            images.append(url)

    play = _pick_play(video)
    read = detail.get("statistics") or {}
    music = detail.get("music") or {}
    author = detail.get("author") or {}

    kind = "images" if images and not play else "video"
    if not play and not images:
        raise ParseError("这条作品没有可下载的内容（可能是直播或已下架）", "no_media")

    return {
        "id": aweme_id,
        "kind": kind,
        "title": (detail.get("desc") or "").strip(),
        "cover": _first((video.get("cover") or {}).get("url_list")) or (images[0] if images else ""),
        "duration": int(video.get("duration") or 0),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "created_at": int(detail.get("create_time") or 0),
        "author": {
            "name": (author.get("nickname") or "").strip(),
            "avatar": _first((author.get("avatar_thumb") or {}).get("url_list")),
        },
        "video": {"url": play},
        "images": images,
        "music": {
            "title": (music.get("title") or "").strip(),
            "author": (music.get("author") or "").strip(),
            "url": _first((music.get("play_url") or {}).get("url_list")),
        },
        "stats": {
            "digg": int(read.get("digg_count") or 0),
            "comment": int(read.get("comment_count") or 0),
            "share": int(read.get("share_count") or 0),
        },
        "share_url": f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
    }


# --------------------------------------------------------------------------- #
# 解析入口
# --------------------------------------------------------------------------- #


class DouyinParser:
    def __init__(self, settings, store, pool) -> None:
        self.settings = settings
        self.store = store
        self.pool = pool

    def parse_text(self, text: str, *, device: str = "", ip: str = "") -> dict:
        text = (text or "").strip()
        if not text:
            raise ParseError("先把抖音分享文案粘贴进来", "empty")
        max_len = int(self.settings.get("limits", "max_text_len", default=600) or 600)
        if len(text) > max_len:
            raise ParseError("内容太长了，只粘贴一条分享文案就行", "too_long")

        kind, aweme_id = pick_target(text)
        started = time.time()
        ttl = int(self.settings.get("parse", "cache_ttl", default=1800) or 0)

        cached = self.store.cache_get(aweme_id, ttl)
        if cached:
            self.store.log_parse(aweme_id=aweme_id, title=cached.get("title", ""), kind=cached.get("kind", kind),
                                 ok=True, duration_ms=int((time.time() - started) * 1000),
                                 device=device, ip=ip)
            result = dict(cached)
            result["cached"] = True
            return result

        try:
            detail = self.pool.detail(aweme_id)
            if not detail:
                raise ParseError("作品不存在或已被删除", "not_found")
            item = normalize(detail)
        except ParseError as exc:
            self.store.log_parse(aweme_id=aweme_id, title="", kind=kind, ok=False,
                                 err=exc.message, duration_ms=int((time.time() - started) * 1000),
                                 device=device, ip=ip)
            raise
        except Exception as exc:  # noqa: BLE001
            self.store.log_parse(aweme_id=aweme_id, title="", kind=kind, ok=False, err=str(exc)[:150],
                                 duration_ms=int((time.time() - started) * 1000), device=device, ip=ip)
            raise ParseError("解析失败，稍后再试一次", "upstream_error") from exc

        self.store.cache_put(aweme_id, item)
        self.store.log_parse(aweme_id=aweme_id, title=item["title"], kind=item["kind"], ok=True,
                             duration_ms=int((time.time() - started) * 1000), device=device, ip=ip)
        item["cached"] = False
        return item

    def fetch_bytes(self, url: str, *, referer: str = "https://www.douyin.com/"):
        """代理下载用：把上游 CDN 的响应原样吐出来。"""
        headers = {
            "User-Agent": UA_DESKTOP,
            "Referer": referer,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        request = urllib.request.Request(url, headers=headers)
        return urllib.request.urlopen(request, timeout=30)
