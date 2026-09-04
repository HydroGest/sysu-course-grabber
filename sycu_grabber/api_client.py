"""中山大学教务选课接口封装。

接口来自原来的 scripts/grab_course.py，只保留与抢课相关的能力：
阶段查询、课程列表、选课、先修课二次确认和退课。
"""

import json
import time
import urllib.error
import urllib.request


BASE = "https://jwxt.sysu.edu.cn/jwxt"
SELECT_INFO_URL = "/choose-course-front-server/classCourseInfo/selectCourseInfo"
COURSE_LIST_URL = "/choose-course-front-server/classCourseInfo/course/list"
COURSE_CHOOSE_URL = "/choose-course-front-server/classCourseInfo/course/choose"
COURSE_BACK_URL = "/choose-course-front-server/classCourseInfo/course/back"
SELECTED_COURSE_URL = "/choose-course-front-server/selectedCourse/list"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# 这些错误继续抢没有意义
STOP_CODES = {
    "52021103",  # 不在选课范围内
    "52021133",  # 上课时间冲突
    "52021134",  # 跨校区课间跨度不足
    "52021135",  # 跨校区课间跨度不足
    "52021136",  # 黑名单
    "52021137",  # 每学期只能两门体育
    "52021138",  # 待筛选体育课超限
    "52021139",  # 已通过该课程
    "52021140",  # 未注册
    "52021141",  # 非本阶段不允许退课
    "52021144",  # 只能选一门校选选修
    "52021146",  # 该阶段不允许退课
    "52021147",  # 预置课程不允许退课
    "52021155",  # 考试时间冲突
    "52021158",  # 公共艺术只能一门
    "52021159",  # 已有公共艺术成绩
}


class ApiError(RuntimeError):
    """教务接口调用失败。"""


class SysuApi:
    """共享一个 Cookie 的教务接口客户端。"""

    def __init__(self):
        self.cookie = ""

    def _headers(self, payload):
        headers = {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE + "/mk/courseSelection/",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        if payload is not None:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, path, payload=None):
        url = BASE + path
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self._headers(payload), method="POST" if data else "GET"
        )
        last_error = None
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                try:
                    return json.loads(e.read().decode("utf-8"))
                except Exception:
                    raise ApiError(f"HTTP {e.code} {e.reason}") from e
            except urllib.error.URLError as e:
                last_error = e
                if attempt < 3:
                    time.sleep(1.5 * attempt)
        raise ApiError(f"网络错误: {last_error.reason}")

    def get_stage(self):
        body = self._request(SELECT_INFO_URL)
        data = body.get("data")
        stage = data if isinstance(data, dict) else body
        if not stage.get("semesterYear") and str(stage.get("code")) != "200":
            raise ApiError(stage.get("message") or "选课阶段信息无效")
        return stage

    def list_courses(self, stage, semester_year, selected_type, selected_cate,
                     page_no, page_size, hidden_conflict="0", hidden_selected="0",
                     hidden_empty="0", vacancy_sort="0", collection_status="0",
                     course_name=""):
        param = {
            "semesterYear": semester_year or stage.get("semesterYear") or "",
            "selectedType": str(selected_type or "1"),
            "selectedCate": str(selected_cate or "11"),
            "hiddenConflictStatus": hidden_conflict,
            "hiddenSelectedStatus": hidden_selected,
            "hiddenEmptyStatus": hidden_empty,
            "vacancySortStatus": vacancy_sort,
            "collectionStatus": collection_status,
        }
        if course_name:
            param["courseName"] = course_name
        body = self._request(COURSE_LIST_URL, {
            "pageNo": page_no,
            "pageSize": page_size,
            "param": param,
        })
        if str(body.get("code")) != "200":
            raise ApiError(body.get("message") or "课程列表查询失败")
        data = body.get("data")
        if not isinstance(data, dict):
            return [], 0
        rows = data.get("rows") or []
        return rows, data.get("total") or len(rows)

    @staticmethod
    def matches(target, row):
        if target.get("courseNum"):
            if str(row.get("courseNum")) == str(target["courseNum"]):
                return True
        if target.get("courseName"):
            name = row.get("courseName") or ""
            if str(target["courseName"]) in name or name in str(target["courseName"]):
                return True
        return False

    def resolve_target(self, target, stage, page_size=50):
        if target.get("clazzId"):
            return {"clazzId": str(target["clazzId"]), "matched": None}
        best = None
        total = None
        for page in range(1, 21):
            rows, total = self.list_courses(
                stage,
                str(target.get("semesterYear") or stage.get("semesterYear") or ""),
                str(target.get("selectedType") or "1"),
                str(target.get("selectedCate") or "11"),
                page,
                page_size,
            )
            for row in rows:
                if not self.matches(target, row):
                    continue
                if best is None:
                    best = row
                elif (row.get("remainNum") or 0) > (best.get("remainNum") or 0):
                    best = row
            if not rows or (total is not None and page * page_size >= total):
                break
        if best is None:
            return None
        return {
            "clazzId": str(best.get("teachingClassId") or best.get("clazzId") or ""),
            "matched": best,
        }

    def search_courses(self, stage, keyword="", selected_type="1", selected_cate="11",
                       page_size=50, max_pages=5):
        keyword = (keyword or "").strip()
        seen = {}
        if keyword:
            first_rows, total = self.list_courses(
                stage, "", selected_type, selected_cate, 1, page_size,
                course_name=keyword,
            )
            if first_rows:
                for row in first_rows:
                    key = str(row.get("teachingClassId") or row.get("clazzId") or "")
                    if key:
                        seen[key] = row
                for page in range(2, max_pages + 1):
                    rows, total = self.list_courses(
                        stage, "", selected_type, selected_cate, page, page_size,
                        course_name=keyword,
                    )
                    for row in rows:
                        key = str(row.get("teachingClassId") or row.get("clazzId") or "")
                        if key:
                            seen[key] = row
                    if not rows or page * page_size >= total:
                        break
                return list(seen.values())
        for page in range(1, max_pages + 1):
            rows, total = self.list_courses(
                stage, "", selected_type, selected_cate, page, page_size
            )
            for row in rows:
                key = str(row.get("teachingClassId") or row.get("clazzId") or "")
                if not key:
                    continue
                if keyword:
                    haystack = "{} {} {}".format(
                        row.get("courseNum") or "",
                        row.get("courseName") or "",
                        row.get("teachingClassName") or "",
                    )
                    for key in ("teachingStaffName", "teachingTeacherName", "teacher",
                                "courseUnitName", "teachingTimePlace"):
                        haystack += " " + str(row.get(key) or "")
                    if keyword not in haystack:
                        continue
                seen[key] = row
            if not rows or page * page_size >= total:
                break
        return list(seen.values())

    def choose(self, clazz_id, selected_type, selected_cate, check):
        payload = {
            "clazzId": clazz_id,
            "selectedType": str(selected_type),
            "selectedCate": str(selected_cate),
            "check": bool(check),
        }
        return self._request(COURSE_CHOOSE_URL, payload)

    def selected_courses(self, page_size=100):
        rows = []
        for page in range(1, 11):
            body = self._request(SELECTED_COURSE_URL, {
                "pageNo": page,
                "pageSize": page_size,
                "total": True,
                "param": {
                    "successStatus": "1",
                    "failureStatus": "0",
                    "retiredClass": "0",
                    "waitingScreen": "1",
                },
            })
            if str(body.get("code")) != "200":
                raise ApiError(body.get("message") or "已选课程查询失败")
            data = body.get("data") or {}
            page_rows = data.get("rows") or []
            rows.extend(page_rows)
            total = data.get("total") or len(page_rows)
            if not page_rows or page * page_size >= int(total):
                break
        return rows

    def back_course(self, course_id, clazz_id, selected_type):
        payload = {
            "courseId": course_id,
            "clazzId": clazz_id,
            "selectedType": str(selected_type),
        }
        return self._request(COURSE_BACK_URL, payload)

    @staticmethod
    def interpret(body):
        code = str(body.get("code") or "")
        data = body.get("data")
        message = body.get("message") or ""
        if code in STOP_CODES:
            return "stop", code, message
        if code in ("200", "52021104"):
            if isinstance(data, dict):
                return "precourse", code, "需要二次确认"
            text = data if isinstance(data, str) else message
            if any(k in text for k in ("成功", "等待筛选", "待筛选")):
                return "success", code, text
            if code == "52021104":
                return "success", code, "已选过该课程"
            return "unknown", code, text
        if code:
            return "retry", code, message
        return "retry", "?", message
