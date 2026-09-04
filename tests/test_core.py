import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sycu_grabber.api_client import SysuApi
from sycu_grabber.engine import GrabEngine, start_target
from sycu_grabber.store import Store


def test_interpret():
    api = SysuApi
    assert api.interpret({"code": "200", "data": "选课成功!"})[0] == "success"
    assert api.interpret({"code": "52021104", "data": ""})[0] == "success"
    assert api.interpret({"code": "200", "data": {"rows": []}})[0] == "precourse"
    assert api.interpret({"code": "52021136", "message": "黑名单"})[0] == "stop"


def test_matches():
    api = SysuApi()
    assert api.matches({"courseName": "羽毛球"}, {"courseName": "羽毛球（提高班）"})
    assert not api.matches({"courseName": "篮球"}, {"courseName": "羽毛球（提高班）"})
    assert api.matches({"courseNum": "MA111"}, {"courseNum": "MA111"})
    assert not api.matches({"courseNum": "MA111"}, {"courseNum": "MA112"})


def test_store_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(tmp)
        target_id = store.add_target({
            "name": "羽毛球",
            "course_name": "羽毛球（提高班）",
            "selected_type": "3",
            "selected_cate": "10",
        })
        target = store.get_target(target_id)
        assert target["name"] == "羽毛球"
        assert target["selected_type"] == "3"
        store.update_target(target_id, {"enabled": True, "status": "running"})
        assert store.get_target(target_id)["enabled"] is True
        store.save_cookie("a=1; b=2")
        assert store.cookie() == "a=1; b=2"
        store.append_log("engine", "info", "test")
        assert store.logs()[0]["message"] == "test"


class FakeApi:
    cookie = "cookie"
    choose_calls = []

    def get_stage(self):
        return {
            "semesterYear": "2026-1",
            "electiveCourseStageName": "测试阶段",
            "chooseCourseStatus": "1",
            "retreatCourseStatus": "0",
        }

    def resolve_target(self, target, stage, page_size=50):
        return {"clazzId": "T1", "matched": None}

    def choose(self, clazz_id, selected_type, selected_cate, check):
        self.choose_calls.append(check)
        if check:
            return {"code": "200", "data": {"rows": []}}
        return {"code": "200", "data": "选课成功!"}

    @staticmethod
    def interpret(body):
        return SysuApi.interpret(body)


def wait_for(predicate, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_engine_once_success():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(tmp)
        store.save_cookie("cookie")
        target_id = store.add_target({
            "name": "高级语言程序设计",
            "course_name": "高级语言程序设计",
            "mode": "once",
            "request_interval": 1.0,
            "auto_confirm": True,
        })
        api = FakeApi()
        engine = GrabEngine(store, api)
        engine.start()
        try:
            start_target(store, target_id, "once")
            engine.wake()
            assert wait_for(lambda: store.get_target(target_id)["status"] == "done")
            assert store.get_target(target_id)["enabled"] is False
            assert len(FakeApi.choose_calls) == 2
        finally:
            engine.stop()


def test_engine_waits_for_cookie():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(tmp)
        target_id = store.add_target({"name": "课", "course_name": "课"})
        api = FakeApi()
        api.cookie = ""
        engine = GrabEngine(store, api)
        engine.start()
        try:
            start_target(store, target_id, "auto")
            engine.wake()
            assert wait_for(lambda: store.get_target(target_id)["status"] == "no_cookie")
            store.save_cookie("cookie")
            api.cookie = "cookie"
            assert store.get_target(target_id)["enabled"] is True
        finally:
            engine.stop()


def test_engine_maps_store_fields_to_api():
    converted = GrabEngine._target_for_api({
        "course_num": "MA111",
        "course_name": "程序设计",
        "clazz_id": "T9",
        "semester_year": "2026-1",
        "selected_type": "2",
        "selected_cate": "30",
    })
    assert converted["clazzId"] == "T9"
    assert converted["courseNum"] == "MA111"
    assert converted["selectedType"] == "2"
    assert converted["selectedCate"] == "30"


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"{name}: OK")
    print("all tests passed")


if __name__ == "__main__":
    main()
