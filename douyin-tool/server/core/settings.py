"""配置读写：config.json 单一文件，改完即时生效，不用重启。"""

from __future__ import annotations

import json
import os
import secrets
import threading

DEFAULTS: dict = {
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        # 部署后填你的域名，例如 https://api.yourdomain.com，用于生成下载直链
        "public_base": "",
        # 后台管理密码，首次启动会自动生成并写回文件
        "admin_token": "",
        # 下载链接签名密钥，泄露会导致被刷流量
        "secret": "",
    },
    "parse": {
        "chrome_path": "",
        "headless": True,
        "workers": 2,
        "seed_aid": "7420371100103707913",
        "cache_ttl": 1800,
        "timeout": 30,
    },
    "limits": {
        "free_per_day": 3,
        "ad_unlock_per_day": 10,
        "ad_unlock_per_view": 1,
        "max_text_len": 600,
    },
    "ads": {
        "enabled": True,
        "rewarded_video": "",
        "banner": "",
        "interstitial": "",
    },
    "app": {
        "notice": "",
        "service_wechat": "",
        "feedback_enabled": True,
        "disclaimer": "本工具仅用于个人学习与备份，请勿用于商业传播。视频版权归原作者所有。",
    },
}

_LOCK = threading.RLock()


class Settings:
    def __init__(self, path: str) -> None:
        self.path = path
        self._data: dict = {}
        self._mtime = 0.0
        self.load()

    # ------------------------------------------------------------------ #
    def load(self) -> dict:
        with _LOCK:
            data = json.loads(json.dumps(DEFAULTS))
            if os.path.isfile(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as fp:
                        saved = json.load(fp)
                    _deep_merge(data, saved)
                except Exception:
                    pass
            changed = False
            if not data["server"]["admin_token"]:
                data["server"]["admin_token"] = _rand_token()
                changed = True
            if not data["server"]["secret"]:
                data["server"]["secret"] = secrets.token_urlsafe(32)
                changed = True
            self._data = data
            self._mtime = _mtime(self.path)
            if changed or not os.path.isfile(self.path):
                self._write(data)
            return data

    def _write(self, data: dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        self._mtime = _mtime(self.path)

    def get(self, *keys, default=None):
        with _LOCK:
            node = self._data
            for key in keys:
                if not isinstance(node, dict) or key not in node:
                    return default
                node = node[key]
            return node

    def section(self, name: str) -> dict:
        value = self.get(name, default={})
        return dict(value) if isinstance(value, dict) else {}

    def patch(self, updates: dict) -> dict:
        """浅合并更新（按 section 合并），返回最新配置。"""
        with _LOCK:
            for section, values in updates.items():
                if isinstance(values, dict) and isinstance(self._data.get(section), dict):
                    self._data[section].update(values)
                else:
                    self._data[section] = values
            self._write(self._data)
            return json.loads(json.dumps(self._data))

    def public(self) -> dict:
        """给小程序看的配置，屏蔽敏感字段。"""
        return {
            "ads": self.section("ads"),
            "limits": self.section("limits"),
            "app": self.section("app"),
        }

    def reload_if_changed(self) -> None:
        if _mtime(self.path) > self._mtime:
            try:
                with open(self.path, "r", encoding="utf-8") as fp:
                    saved = json.load(fp)
                data = json.loads(json.dumps(DEFAULTS))
                _deep_merge(data, saved)
                if not data["server"]["admin_token"]:
                    data["server"]["admin_token"] = self._data["server"]["admin_token"]
                if not data["server"]["secret"]:
                    data["server"]["secret"] = self._data["server"]["secret"]
                with _LOCK:
                    self._data = data
                    self._mtime = _mtime(self.path)
            except Exception:
                pass


def _deep_merge(base: dict, extra: dict) -> None:
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _rand_token() -> str:
    return secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
