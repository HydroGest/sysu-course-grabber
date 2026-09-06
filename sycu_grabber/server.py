"""本机 HTTP 服务与 API。"""

import json
import os
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sycu_grabber import __version__
from sycu_grabber.api_client import SysuApi
from sycu_grabber.browser_importer import BrowserImporter
from sycu_grabber.engine import GrabEngine, start_target
from sycu_grabber.schedule import build_schedule, candidate_conflicts, sessions_from_selected
from sycu_grabber.store import Store


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_UI = PROJECT_ROOT / "webui"
EXTENSION_DIR = PROJECT_ROOT / "extension"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def _read_json(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    try:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("JSON 格式错误")


def _client_local(handler):
    return handler.client_address[0] in ("127.0.0.1", "::1")


SCOPE_CATE = {"1": "11", "2": "30", "3": "10", "4": "30"}
AUTO_SCOPES = [
    ("1", "10"), ("1", "11"), ("1", "21"), ("1", "30"),
    ("2", "10"), ("2", "21"), ("2", "30"),
    ("3", "10"), ("3", "30"),
    ("4", "10"), ("4", "21"), ("4", "30"),
]


def search_courses_smart(api, stage, keyword, scope):
    if scope == "auto":
        found = []
        for selected_type, selected_cate in AUTO_SCOPES:
            rows = api.search_courses(
                stage, keyword, selected_type, selected_cate,
                page_size=50, max_pages=3,
            )
            if rows:
                for row in rows:
                    row["searchType"] = selected_type
                    row["searchCate"] = selected_cate
                found = rows
                break
        return found
    selected_type = scope or "1"
    selected_cate = SCOPE_CATE.get(selected_type, "11")
    return api.search_courses(
        stage, keyword, selected_type, selected_cate,
        page_size=50, max_pages=5,
    )


class App:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.store = Store(data_dir)
        self.api = SysuApi()
        self.api.cookie = self.store.cookie()
        self.engine = GrabEngine(self.store, self.api)
        self.engine.start()
        self.engine.refresh_stage()
        self.browser = BrowserImporter(self.data_dir, self.accept_browser_cookie)

    def set_cookie(self, cookie):
        self.store.save_cookie(cookie)
        self.api.cookie = cookie
        self.store.append_log("session", "info", "Cookie 已更新")
        threading.Thread(target=lambda: self.engine.refresh_stage(force=True), daemon=True).start()
        self.engine.wake()

    def accept_browser_cookie(self, cookie):
        """Only import a browser login if the教务接口 can actually verify it."""
        old_cookie = self.api.cookie
        self.api.cookie = cookie
        info = {"state": "error"}
        try:
            info = self.engine.refresh_stage(force=True)
        except Exception as e:
            self.api.cookie = old_cookie
            self.store.append_log("session", "warn", f"浏览器登录校验失败: {e}")
            return False
        if info.get("state") != "ok":
            self.api.cookie = old_cookie
            self.store.append_log("session", "warn", "浏览器登录校验未通过")
            return False
        self.store.save_cookie(cookie)
        self.store.append_log("session", "info", "浏览器登录已通过教务接口校验")
        self.engine.wake()
        return True

    def target_payload(self, data):
        name = str(data.get("name") or "").strip()
        course_name = str(data.get("courseName") or "").strip()
        course_num = str(data.get("courseNum") or "").strip()
        clazz_id = str(data.get("clazzId") or "").strip()
        if not name:
            name = course_name or course_num or "未命名目标"
        payload = {
            "name": name,
            "course_name": course_name,
            "course_num": course_num,
            "clazz_id": clazz_id,
            "semester_year": str(data.get("semesterYear") or "").strip(),
            "selected_type": str(data.get("selectedType") or "1"),
            "selected_cate": str(data.get("selectedCate") or "11"),
            "priority": int(data.get("priority") or 100),
            "mode": "auto" if str(data.get("mode") or "auto") != "once" else "once",
            "start_at": (str(data["startAt"]).strip() if data.get("startAt") else None),
            "max_minutes": float(data.get("maxMinutes") or 60),
            "request_interval": max(1.0, float(data.get("requestInterval") or 1.5)),
            "auto_confirm": bool(data.get("autoConfirm", True)),
            "status": "idle",
        }
        return payload


def make_handler(ctx, host):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SYSUCourseGrabber/" + __version__

        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code, message):
            self._json(code, {"error": message})

        def log_message(self, fmt, *args):
            pass

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/"):
                self._api_get(path, urllib.parse.parse_qs(parsed.query))
                return
            self._static(path)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._api_post(parsed.path)
                return
            self._error(404, "not found")

        def _static(self, path):
            if path in ("/", ""):
                path = "/index.html"
            try:
                rel = urllib.parse.unquote(path).lstrip("/")
                target = (WEB_UI / rel).resolve()
                if not str(target).startswith(str(WEB_UI.resolve())):
                    raise ValueError("bad path")
                if not target.is_file():
                    raise FileNotFoundError
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", MIME.get(target.suffix.lower(), "application/octet-stream"))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self._error(404, "not found")

        def _api_get(self, path, query):
            if path == "/api/health":
                stage = dict(ctx.engine.stage_info)
                summary = ctx.store.summary()
                self._json(200, {
                    "app": "SYSU Course Grabber",
                    "version": __version__,
                    "cookie": bool(ctx.api.cookie),
                    "cookie_at": ctx.store.cookie_at(),
                    "engine": ctx.engine.is_running(),
                    "stage": stage,
                    "targets": summary,
                    "now": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                })
                return
            if path == "/api/stage":
                stage = ctx.engine.refresh_stage(force=True)
                self._json(200, stage)
                return
            if path == "/api/session/login-status":
                self._json(200, ctx.browser.snapshot())
                return
            if path == "/api/targets":
                self._json(200, {"targets": ctx.store.list_targets()})
                return
            if path == "/api/logs":
                limit = int((query.get("limit") or ["100"])[0])
                self._json(200, {"logs": ctx.store.logs(limit)})
                return
            if path == "/api/logs/clear":
                ctx.store.clear_logs()
                self._json(200, {"ok": True})
                return
            if path == "/api/context":
                self._json(200, {
                    "extension_dir": str(EXTENSION_DIR),
                    "server": f"http://{host}:{self.server.server_port}",
                    "chrome": os.path.exists(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                    "edge": os.path.exists(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
                             or os.path.exists(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
                })
                return
            if path == "/api/search":
                if not ctx.api.cookie:
                    self._json(409, {"error": "no_cookie", "message": "等待浏览器同步 Cookie"})
                    return
                try:
                    stage = ctx.engine.refresh_stage(force=True)
                    if stage.get("state") != "ok":
                        self._json(409, {"error": "stage", "message": stage.get("message") or "阶段信息不可用"})
                        return
                    rows = search_courses_smart(
                        ctx.api,
                        ctx.engine._stage_cache,
                        keyword=(query.get("q") or [""])[0],
                        scope=(query.get("type") or ["auto"])[0],
                    )
                    if rows:
                        try:
                            selected_rows = ctx.api.selected_courses()
                            for row in rows:
                                row["conflicts"] = candidate_conflicts(
                                    row.get("courseName") or "",
                                    row.get("courseNum") or "",
                                    row.get("teachingClassId") or row.get("clazzId") or "",
                                    row.get("teachingTimePlace") or "",
                                    selected_rows,
                                )
                        except Exception:
                            pass
                    self._json(200, {"rows": rows})
                except Exception as e:
                    self._json(502, {"error": str(e), "message": "课程搜索失败"})
                return
            if path == "/api/selected":
                if not ctx.api.cookie:
                    self._json(409, {"error": "no_cookie", "message": "等待浏览器同步 Cookie"})
                    return
                try:
                    rows = ctx.api.selected_courses()
                    summary = {
                        "course": 0,
                        "credit": 0.0,
                    }
                    if rows:
                        first = rows[0]
                        summary = {
                            "course": first.get("sumCourse") or len(rows),
                            "credit": first.get("sumCredit") or 0.0,
                            "public_required": first.get("gbCount") or 0,
                            "public_elective": first.get("gxCount") or 0,
                            "major_required": first.get("zbCount") or 0,
                            "major_elective": first.get("zxCount") or 0,
                            "honor": first.get("rykcCount") or 0,
                            "cross_major": first.get("kzyCount") or 0,
                        }
                    self._json(200, {"rows": rows, "summary": summary})
                except Exception as e:
                    self._json(502, {"error": str(e), "message": "已选课程查询失败"})
                return
            if path == "/api/schedule":
                if not ctx.api.cookie:
                    self._json(409, {"error": "no_cookie", "message": "等待浏览器同步 Cookie"})
                    return
                try:
                    rows = ctx.api.selected_courses()
                    result = build_schedule(rows)
                    self._json(200, result)
                except Exception as e:
                    self._json(502, {"error": str(e), "message": "课程表查询失败"})
                return
            self._error(404, "not found")

        def _api_post(self, path):
            if path == "/api/cookie":
                if not _client_local(self):
                    self._error(403, "local only")
                    return
                try:
                    data = _read_json(self)
                except ValueError as e:
                    self._error(400, str(e))
                    return
                cookie = str(data.get("cookie") or "").strip()
                if not cookie:
                    self._error(400, "empty cookie")
                    return
                ctx.set_cookie(cookie)
                self._json(200, {"ok": True})
                return
            if path == "/api/targets":
                try:
                    payload = ctx.target_payload(_read_json(self))
                    target_id = ctx.store.add_target(payload)
                    self._json(201, {"ok": True, "id": target_id})
                except Exception as e:
                    self._error(400, str(e))
                return
            if path == "/api/session/login":
                self._json(200, ctx.browser.start_login())
                return
            if path == "/api/session/cancel":
                ctx.browser.stop()
                self._json(200, {"ok": True})
                return
            if path == "/api/shutdown":
                self._json(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if path == "/api/open/extensions":
                target_url = "edge://extensions" if os.path.exists(
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                ) else "chrome://extensions"
                threading.Thread(target=lambda: webbrowser.open(target_url), daemon=True).start()
                self._json(200, {"ok": True})
                return
            m = re.fullmatch(r"/api/targets/(\d+)/([a-z-]+)", path)
            if not m:
                self._error(404, "not found")
                return
            target_id = int(m.group(1))
            action = m.group(2)
            try:
                data = _read_json(self) if self.headers.get("Content-Length") else {}
            except ValueError as e:
                self._error(400, str(e))
                return
            try:
                if action == "update":
                    allowed = {
                        "name": "name", "courseName": "course_name",
                        "courseNum": "course_num", "clazzId": "clazz_id",
                        "semesterYear": "semester_year",
                        "selectedType": "selected_type", "selectedCate": "selected_cate",
                        "priority": "priority", "mode": "mode",
                        "startAt": "start_at", "maxMinutes": "max_minutes",
                        "requestInterval": "request_interval", "autoConfirm": "auto_confirm",
                    }
                    patch = {}
                    for k, db in allowed.items():
                        if k not in data:
                            continue
                        v = data[k]
                        if k == "startAt":
                            v = str(v).strip() if v else None
                        elif k == "autoConfirm":
                            v = bool(v)
                        elif k in ("priority",):
                            v = int(v)
                        elif k in ("maxMinutes", "requestInterval"):
                            v = max(1.0, float(v)) if k == "requestInterval" else float(v)
                        patch[db] = v
                    ctx.store.update_target(target_id, patch)
                    self._json(200, {"ok": True})
                    return
                if action == "start":
                    mode = str(data.get("mode") or "auto")
                    start_target(ctx.store, target_id, mode)
                    ctx.engine.wake()
                    self._json(200, {"ok": True})
                    return
                if action == "once":
                    start_target(ctx.store, target_id, "once")
                    ctx.engine.wake()
                    self._json(200, {"ok": True})
                    return
                if action == "stop":
                    target = ctx.store.get_target(target_id)
                    if target and target["status"] not in ("done", "aborted", "timeout"):
                        ctx.store.update_target(target_id, {
                            "enabled": 0,
                            "status": "idle",
                            "last_message": "",
                        })
                    elif target:
                        ctx.store.update_target(target_id, {"enabled": 0})
                    self._json(200, {"ok": True})
                    return
                if action == "delete":
                    ctx.store.delete_target(target_id)
                    self._json(200, {"ok": True})
                    return
                if action == "paste-cookie":
                    if not _client_local(self):
                        self._error(403, "local only")
                        return
                    cookie = str(data.get("cookie") or "").strip()
                    if not cookie:
                        self._error(400, "empty cookie")
                        return
                    ctx.set_cookie(cookie)
                    self._json(200, {"ok": True})
                    return
            except KeyError as e:
                self._error(404, str(e))
                return
            except Exception as e:
                self._error(400, str(e))
                return
            self._error(404, "not found")

    return Handler


def create_httpd(host, port, data_dir):
    ctx = App(data_dir)
    handler = make_handler(ctx, host)
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    httpd.ctx = ctx
    return httpd


def run_server(httpd):
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.ctx.engine.stop()
        httpd.ctx.browser.stop()
