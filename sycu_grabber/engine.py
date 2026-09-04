"""预定与自动抢课引擎。"""

import random
import threading
import time
from datetime import datetime


TERMINAL_STATUSES = {"done", "aborted", "timeout", "needs_confirm"}


def parse_local_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class GrabEngine:
    """后台单线程循环，一次只发一个选课请求。

    每个目标按优先级轮流处理；请求间隔跟随目标自身的
    request_interval，且低于 1 秒的值会被强制抬到 1 秒。
    """

    def __init__(self, store, api):
        self.store = store
        self.api = api
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None
        self._stage_cache = None
        self._stage_ts = 0.0
        self.stage_info = {"state": "unknown"}
        self._log_ts = {}

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="grab-engine", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def wake(self):
        self._wake.set()

    def _log_target(self, target_id, message, level="info", force=False):
        now = time.monotonic()
        last = self._log_ts.get(target_id, 0)
        if force or now - last >= 60:
            self.store.append_log("engine", level, message)
            self._log_ts[target_id] = now

    def refresh_stage(self, force=False):
        now = time.monotonic()
        if not force and self._stage_cache and now - self._stage_ts < 60:
            return dict(self.stage_info)
        if not self.api.cookie:
            self.stage_info = {
                "state": "no_cookie",
                "semester": "",
                "stage_name": "",
                "choose_open": "",
                "back_open": "",
                "message": "尚未收到教务登录 Cookie",
            }
            return dict(self.stage_info)
        try:
            stage = self.api.get_stage()
        except Exception as e:
            message = str(e) or e.__class__.__name__
            self.stage_info = {
                "state": "error",
                "semester": "",
                "stage_name": "",
                "choose_open": "",
                "back_open": "",
                "message": message,
            }
            return dict(self.stage_info)
        self._stage_cache = stage
        self._stage_ts = now
        self.stage_info = {
            "state": "ok",
            "semester": stage.get("semesterYear") or "",
            "stage_name": stage.get("electiveCourseStageName") or "",
            "choose_open": str(stage.get("chooseCourseStatus") or ""),
            "back_open": str(stage.get("retreatCourseStatus") or ""),
            "message": "",
        }
        return dict(self.stage_info)

    def _wait_until(self, delay):
        self._wake.wait(max(0.2, float(delay)))
        self._wake.clear()

    def _run(self):
        next_at = {}
        while not self._stop.is_set():
            try:
                targets = self.store.list_targets()
                active = [t for t in targets if t["enabled"]]
                due = None
                now_mono = time.monotonic()
                now_dt = datetime.now()
                for target in sorted(active, key=lambda t: (t["priority"], t["id"])):
                    if self._is_stale_enabled(target):
                        self.store.update_target(target["id"], {"enabled": 0})
                        continue
                    start = parse_local_dt(target["start_at"])
                    if start and start > now_dt:
                        if target["status"] != "scheduled":
                            self.store.update_target(target["id"], {"status": "scheduled"})
                        continue
                    if target["status"] in TERMINAL_STATUSES:
                        self.store.update_target(target["id"], {"enabled": 0})
                        continue
                    if self._is_timeout(target, now_dt):
                        continue
                    target_id = target["id"]
                    if target_id not in next_at:
                        next_at[target_id] = 0.0
                    if next_at[target_id] <= now_mono:
                        due = target
                        break
                if due is None:
                    wait = 1.0
                    upcoming = []
                    for target in active:
                        start = parse_local_dt(target["start_at"])
                        if start and start > now_dt:
                            upcoming.append((start - now_dt).total_seconds())
                        if target["id"] in next_at:
                            upcoming.append(next_at[target["id"]] - time.monotonic())
                    if upcoming:
                        wait = max(0.2, min(upcoming))
                    self._wait_until(wait)
                    continue

                outcome = self._attempt(due)
                if outcome and outcome.get("blacklist"):
                    self._disable_all("黑名单提示，已停止全部抢课任务")
                    self.store.append_log("engine", "error", "检测到黑名单，全部任务已停止")
                    continue
                if due["mode"] == "once":
                    terminal = outcome and outcome.get("terminal")
                    if terminal not in ("done", "aborted", "needs_confirm"):
                        self.store.update_target(due["id"], {"enabled": 0, "status": "tried"})
                    else:
                        self.store.update_target(due["id"], {"enabled": 0})
                interval = max(1.0, float(due.get("request_interval") or 1.5))
                next_at[due["id"]] = time.monotonic() + interval * random.uniform(0.8, 1.5)
            except Exception as e:
                self.store.append_log("engine", "error", f"引擎内部错误: {e}")
                self._wait_until(2.0)

    def _is_stale_enabled(self, target):
        return target["status"] in TERMINAL_STATUSES and target["enabled"]

    def _is_timeout(self, target, now_dt):
        started = parse_local_dt(target["started_at"])
        if not started or not target.get("max_minutes"):
            return False
        elapsed = (now_dt - started).total_seconds()
        if elapsed <= float(target["max_minutes"]) * 60:
            return False
        self.store.update_target(target["id"], {
            "enabled": 0,
            "status": "timeout",
            "last_message": "已达到设定的最长抢课时间",
        })
        self.store.append_log("engine", "warn", f"{target['name']} 已超时")
        return True

    def _disable_all(self, message):
        for target in self.store.list_targets():
            if target["enabled"]:
                self.store.update_target(target["id"], {
                    "enabled": 0,
                    "status": "aborted",
                    "last_message": message,
                })

    @staticmethod
    def _target_for_api(target):
        """Store rows use snake_case; the relay API expects camelCase."""
        return {
            "courseNum": target.get("course_num") or "",
            "courseName": target.get("course_name") or "",
            "clazzId": target.get("clazz_id") or "",
            "semesterYear": target.get("semester_year") or "",
            "selectedType": target.get("selected_type") or "1",
            "selectedCate": target.get("selected_cate") or "11",
        }

    def _attempt(self, target):
        target_id = target["id"]
        attempts = int(target.get("attempts") or 0) + 1
        started_at = target.get("started_at") or datetime.now().isoformat(timespec="seconds")
        if not self.api.cookie:
            self.store.update_target(target_id, {
                "attempts": attempts,
                "status": "no_cookie",
                "started_at": started_at,
                "last_message": "等待浏览器同步登录 Cookie",
            })
            self._log_target(target_id, f"{target['name']}: 等待 Cookie", "warn")
            return None

        if self.stage_info.get("state") != "ok" or not self._stage_cache:
            info = self.refresh_stage(force=True)
            if info.get("state") != "ok":
                message = info.get("message") or "阶段查询失败"
                self.store.update_target(target_id, {
                    "attempts": attempts,
                    "status": "running",
                    "started_at": started_at,
                    "last_message": message,
                })
                self._log_target(target_id, f"{target['name']}: 阶段查询失败 {message}", "error")
                return None
        stage = self._stage_cache

        self.store.update_target(target_id, {
            "attempts": attempts,
            "status": "running",
            "started_at": started_at,
        })
        try:
            resolved = self.api.resolve_target(self._target_for_api(target), stage, 50)
        except Exception as e:
            message = str(e) or e.__class__.__name__
            self.store.update_target(target_id, {
                "last_code": "resolve_error",
                "last_message": message,
            })
            self._log_target(target_id, f"{target['name']}: 解析教学班失败 {message}", "error")
            return None
        if resolved is None or not resolved.get("clazzId"):
            self.store.update_target(target_id, {
                "last_code": "not_found",
                "last_message": "暂未匹配到可抢教学班",
            })
            self._log_target(target_id, f"{target['name']}: 暂未匹配到可抢教学班")
            return None

        try:
            body = self.api.choose(
                resolved["clazzId"],
                target.get("selected_type") or "1",
                target.get("selected_cate") or "11",
                True,
            )
        except Exception as e:
            message = str(e) or e.__class__.__name__
            self.store.update_target(target_id, {
                "last_code": "request_error",
                "last_message": message,
            })
            self._log_target(target_id, f"{target['name']}: 选课请求失败 {message}", "error")
            return None

        state, code, msg = self.api.interpret(body)
        if state == "precourse":
            if not target.get("auto_confirm"):
                self.store.update_target(target_id, {
                    "enabled": 0,
                    "status": "needs_confirm",
                    "last_code": code,
                    "last_message": "需要二次确认，已暂停等待人工处理",
                })
                self.store.append_log("engine", "warn",
                                      f"{target['name']}: 需要二次确认，已暂停")
                return {"terminal": "needs_confirm"}
            try:
                body = self.api.choose(
                    resolved["clazzId"],
                    target.get("selected_type") or "1",
                    target.get("selected_cate") or "11",
                    False,
                )
            except Exception as e:
                message = str(e) or e.__class__.__name__
                self.store.update_target(target_id, {
                    "last_code": "confirm_error",
                    "last_message": message,
                })
                self._log_target(target_id, f"{target['name']}: 二次确认失败 {message}", "error")
                return None
            state, code, msg = self.api.interpret(body)

        message = msg or ""
        self.store.update_target(target_id, {"last_code": code, "last_message": message})
        if state == "success":
            self.store.update_target(target_id, {
                "enabled": 0,
                "status": "done",
                "last_message": message or "选课成功",
            })
            self.store.append_log("engine", "info", f"{target['name']}: 选课成功")
            return {"terminal": "done"}
        if state == "stop":
            self.store.update_target(target_id, {
                "enabled": 0,
                "status": "aborted",
                "last_message": message or "任务已停止",
            })
            self.store.append_log("engine", "error",
                                  f"{target['name']}: 停止 {code} {message}")
            return {"terminal": "aborted", "blacklist": code == "52021136"}
        self._log_target(target_id, f"{target['name']}: code={code} {message}")
        return None


def start_target(store, target_id, mode):
    target = store.get_target(target_id)
    if target is None:
        raise KeyError("目标不存在")
    start = parse_local_dt(target["start_at"])
    status = "scheduled" if start and start > datetime.now() else "running"
    return store.update_target(target_id, {
        "enabled": 1,
        "mode": mode if mode in ("auto", "once") else "auto",
        "status": status,
        "started_at": None if status == "scheduled" else target.get("started_at"),
    })
