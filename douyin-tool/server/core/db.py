"""SQLite 存储：解析记录、结果缓存、意见反馈。

单文件数据库，方便备份（直接拷 data.db）。所有写操作串行化，够这个量级用。
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS parses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aweme_id TEXT, title TEXT, kind TEXT,
    ok INTEGER NOT NULL DEFAULT 0, err TEXT,
    duration_ms INTEGER, device TEXT, ip TEXT,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_parses_ts ON parses(ts);
CREATE TABLE IF NOT EXISTS cache (
    aweme_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL, contact TEXT, device TEXT, ts INTEGER NOT NULL
);
"""


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # -- 解析记录 -------------------------------------------------------- #
    def log_parse(self, *, aweme_id: str, title: str, kind: str, ok: bool,
                  err: str = "", duration_ms: int = 0, device: str = "", ip: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO parses (aweme_id,title,kind,ok,err,duration_ms,device,ip,ts)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (aweme_id, (title or "")[:120], kind, 1 if ok else 0, (err or "")[:200],
                 duration_ms, device, ip, int(time.time())),
            )
            self._conn.commit()

    def stats(self, days: int = 7) -> dict:
        since = int(time.time()) - days * 86400
        today = int(time.time()) // 86400 * 86400
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) c, SUM(ok) ok, AVG(duration_ms) avg_ms FROM parses WHERE ts>=?", (since,))
            row = cur.fetchone()
            total = row["c"] or 0
            ok = row["ok"] or 0
            avg_ms = int(row["avg_ms"] or 0)
            cur = self._conn.execute(
                "SELECT COUNT(*) c, SUM(ok) ok FROM parses WHERE ts>=?", (today,))
            trow = cur.fetchone()
            cur = self._conn.execute(
                "SELECT date(ts,'unixepoch','localtime') d, COUNT(*) c, SUM(ok) ok"
                " FROM parses WHERE ts>=? GROUP BY d ORDER BY d", (since,))
            trend = [{"date": r["d"], "total": r["c"], "ok": r["ok"] or 0} for r in cur.fetchall()]
            cur = self._conn.execute(
                "SELECT err, COUNT(*) c FROM parses WHERE ok=0 AND ts>=? AND err<>''"
                " GROUP BY err ORDER BY c DESC LIMIT 8", (since,))
            errors = [{"err": r["err"], "count": r["c"]} for r in cur.fetchall()]
            cur = self._conn.execute(
                "SELECT title, COUNT(*) c FROM parses WHERE ok=1 AND ts>=?"
                " GROUP BY aweme_id ORDER BY c DESC LIMIT 8", (since,))
            hot = [{"title": r["title"], "count": r["c"]} for r in cur.fetchall()]
            cur = self._conn.execute("SELECT COUNT(*) c FROM cache")
            cached = cur.fetchone()["c"]
            cur = self._conn.execute("SELECT COUNT(*) c FROM feedback WHERE ts>=?", (since,))
            feedback_count = cur.fetchone()["c"]
        return {
            "total": total, "ok": ok,
            "rate": round(ok / total * 100, 1) if total else 0,
            "avg_ms": avg_ms,
            "today": {"total": trow["c"] or 0, "ok": trow["ok"] or 0},
            "trend": trend, "errors": errors, "hot": hot,
            "cache": cached, "feedback": feedback_count,
        }

    def feedback_list(self, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT content,contact,device,ts FROM feedback ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    # -- 缓存 ------------------------------------------------------------ #
    def cache_get(self, aweme_id: str, ttl: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute("SELECT payload, ts FROM cache WHERE aweme_id=?", (aweme_id,))
            row = cur.fetchone()
        if not row:
            return None
        if ttl and time.time() - row["ts"] > ttl:
            return None
        try:
            return json.loads(row["payload"])
        except Exception:
            return None

    def cache_put(self, aweme_id: str, payload: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO cache (aweme_id,payload,ts) VALUES (?,?,?)"
                " ON CONFLICT(aweme_id) DO UPDATE SET payload=excluded.payload, ts=excluded.ts",
                (aweme_id, json.dumps(payload, ensure_ascii=False), int(time.time())),
            )
            self._conn.commit()

    def cache_clear(self) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM cache")
            self._conn.commit()
            return cur.rowcount

    # -- 反馈 ------------------------------------------------------------ #
    def add_feedback(self, content: str, contact: str = "", device: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO feedback (content,contact,device,ts) VALUES (?,?,?,?)",
                (content[:1000], contact[:100], device[:64], int(time.time())),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


def open_store(path: str) -> Store:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return Store(path)
