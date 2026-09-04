"""本地 SQLite 数据、日志与 Cookie 存储。"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


TARGET_COLUMNS = {
    "name", "course_name", "course_num", "clazz_id", "semester_year",
    "selected_type", "selected_cate", "priority", "enabled", "mode",
    "start_at", "max_minutes", "request_interval", "auto_confirm",
    "status", "attempts", "started_at", "last_code", "last_message",
}


def _now():
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "grabber.db"
        self.cookie_path = self.data_dir / "cookie.txt"
        self._cookie = ""
        self._init_db()
        self._cookie = self._read_cookie()

    def _conn(self):
        con = sqlite3.connect(self.db_path, timeout=15)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def connect(self):
        con = self._conn()
        try:
            with con:
                yield con
        finally:
            con.close()

    def _init_db(self):
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    course_name TEXT NOT NULL DEFAULT '',
                    course_num TEXT NOT NULL DEFAULT '',
                    clazz_id TEXT NOT NULL DEFAULT '',
                    semester_year TEXT NOT NULL DEFAULT '',
                    selected_type TEXT NOT NULL DEFAULT '1',
                    selected_cate TEXT NOT NULL DEFAULT '11',
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    mode TEXT NOT NULL DEFAULT 'auto',
                    start_at TEXT,
                    max_minutes REAL NOT NULL DEFAULT 60,
                    request_interval REAL NOT NULL DEFAULT 1.5,
                    auto_confirm INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'idle',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT,
                    last_code TEXT NOT NULL DEFAULT '',
                    last_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                """
            )

    def _read_cookie(self):
        try:
            value = self.cookie_path.read_text(encoding="utf-8").strip()
            return value
        except FileNotFoundError:
            return ""

    def cookie(self):
        return self._cookie

    def cookie_at(self):
        try:
            return self.cookie_path.stat().st_mtime
        except OSError:
            return 0

    def save_cookie(self, cookie):
        self._cookie = (cookie or "").strip()
        self.cookie_path.write_text(self._cookie, encoding="utf-8")

    @staticmethod
    def _row(row):
        return {
            "id": row["id"],
            "name": row["name"],
            "course_name": row["course_name"],
            "course_num": row["course_num"],
            "clazz_id": row["clazz_id"],
            "semester_year": row["semester_year"],
            "selected_type": row["selected_type"],
            "selected_cate": row["selected_cate"],
            "priority": row["priority"],
            "enabled": bool(row["enabled"]),
            "mode": row["mode"],
            "start_at": row["start_at"],
            "max_minutes": row["max_minutes"],
            "request_interval": row["request_interval"],
            "auto_confirm": bool(row["auto_confirm"]),
            "status": row["status"],
            "attempts": row["attempts"],
            "started_at": row["started_at"],
            "last_code": row["last_code"],
            "last_message": row["last_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_targets(self):
        with self.connect() as con:
            rows = con.execute("SELECT * FROM targets ORDER BY priority ASC, id ASC").fetchall()
        return [self._row(r) for r in rows]

    def get_target(self, target_id):
        with self.connect() as con:
            row = con.execute("SELECT * FROM targets WHERE id=?", (target_id,)).fetchone()
        return self._row(row) if row else None

    def add_target(self, values):
        now = _now()
        defaults = {
            "course_name": "", "course_num": "", "clazz_id": "", "semester_year": "",
            "selected_type": "1", "selected_cate": "11", "priority": 100,
            "enabled": 0, "mode": "auto", "start_at": None, "max_minutes": 60.0,
            "request_interval": 1.5, "auto_confirm": 1, "status": "idle",
            "attempts": 0, "started_at": None, "last_code": "", "last_message": "",
        }
        row = {**defaults, **values}
        row["enabled"] = int(bool(row["enabled"]))
        row["auto_confirm"] = int(bool(row["auto_confirm"]))
        with self.connect() as con:
            cur = con.execute(
                """
                INSERT INTO targets (
                    name, course_name, course_num, clazz_id, semester_year,
                    selected_type, selected_cate, priority, enabled, mode,
                    start_at, max_minutes, request_interval, auto_confirm,
                    status, attempts, started_at, last_code, last_message,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["name"], row["course_name"], row["course_num"], row["clazz_id"],
                    row["semester_year"], row["selected_type"], row["selected_cate"],
                    row["priority"], row["enabled"], row["mode"], row["start_at"],
                    row["max_minutes"], row["request_interval"], row["auto_confirm"],
                    row["status"], row["attempts"], row["started_at"], row["last_code"],
                    row["last_message"], now, now,
                ),
            )
            return cur.lastrowid

    def update_target(self, target_id, patch):
        patch = dict(patch)
        patch.pop("id", None)
        bad = set(patch) - TARGET_COLUMNS
        if bad:
            raise ValueError(f"unknown fields: {sorted(bad)}")
        if "enabled" in patch:
            patch["enabled"] = int(bool(patch["enabled"]))
        if "auto_confirm" in patch:
            patch["auto_confirm"] = int(bool(patch["auto_confirm"]))
        patch["updated_at"] = _now()
        keys = ", ".join(f"{k}=?" for k in patch)
        values = list(patch.values())
        values.append(target_id)
        with self.connect() as con:
            con.execute(f"UPDATE targets SET {keys} WHERE id=?", values)
        return self.get_target(target_id)

    def delete_target(self, target_id):
        with self.connect() as con:
            con.execute("DELETE FROM targets WHERE id=?", (target_id,))

    def append_log(self, source, level, message):
        with self.connect() as con:
            con.execute(
                "INSERT INTO logs (ts, source, level, message) VALUES (?,?,?,?)",
                (_now(), source, level, message),
            )

    def logs(self, limit=100):
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def clear_logs(self):
        with self.connect() as con:
            con.execute("DELETE FROM logs")

    def summary(self):
        targets = self.list_targets()
        return {
            "total": len(targets),
            "enabled": sum(1 for t in targets if t["enabled"]),
            "done": sum(1 for t in targets if t["status"] == "done"),
            "running": sum(1 for t in targets if t["enabled"] and t["status"] == "running"),
        }
