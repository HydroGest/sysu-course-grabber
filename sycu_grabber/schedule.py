"""课程时间文本解析与冲突检测。

教务返回的 teachingTimePlace 形如：
  王远世;1-8每周星期一第3节-第4节;南校园 第五教学楼(逸夫楼)逸102
"""

import re
from dataclasses import dataclass


WEEKDAY = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}
WEEK_NAME = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
SESSION_RE = re.compile(
    r"^(?:([^;]*);)?"
    r"([\d,\-()\u5355\u53cc]*)?"
    r"每周星期([一二三四五六日天])"
    r"第(\d+)节(?:-第?(\d+)节)?"
    r"(?:;([^;]*))?$"
)


@dataclass
class CourseSession:
    course_name: str
    course_num: str
    teacher: str
    weekday: int
    start_section: int
    end_section: int
    weeks: frozenset
    place: str
    raw: str

    @property
    def section_text(self):
        if self.start_section == self.end_section:
            return f"第{self.start_section}节"
        return f"第{self.start_section}-{self.end_section}节"

    @property
    def week_text(self):
        nums = sorted(self.weeks)
        if not nums:
            return ""
        parts = []
        start = prev = nums[0]
        for n in nums[1:]:
            if n == prev + 1:
                prev = n
                continue
            parts.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = n
        parts.append(str(start) if start == prev else f"{start}-{prev}")
        return ",".join(parts)


def _expand_weeks(value):
    if not value:
        return set()
    weeks = set()
    for token in re.findall(r"(\d+)(?:-(\d+))?(?:\(([\u5355\u53cc])\))?", value):
        start = int(token[0])
        end = int(token[1] or token[0])
        parity = token[2]
        for week in range(start, end + 1):
            if parity == "单" and week % 2 == 0:
                continue
            if parity == "双" and week % 2 == 1:
                continue
            weeks.add(week)
    return weeks


def parse_course_sessions(course_name, course_num, text):
    """Parse one course row's teachingTimePlace into concrete sessions."""
    sessions = []
    for raw in (text or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        match = SESSION_RE.match(raw)
        if not match:
            continue
        teacher, week_text, weekday, start, end, place = match.groups()
        start = int(start)
        end = int(end or start)
        if end < start:
            end = start
        sessions.append(CourseSession(
            course_name=course_name,
            course_num=course_num or "",
            teacher=(teacher or "").strip(),
            weekday=WEEKDAY[weekday],
            start_section=start,
            end_section=end,
            weeks=frozenset(_expand_weeks(week_text) or range(1, 26)),
            place=(place or "").strip(),
            raw=raw,
        ))
    return sessions


def overlap(a, b):
    return (
        a.weekday == b.weekday
        and a.start_section <= b.end_section
        and b.start_section <= a.end_section
        and bool(a.weeks & b.weeks)
    )


def describe_conflict(a, b):
    weekdays = WEEK_NAME.get(a.weekday, "")
    common = sorted(a.weeks & b.weeks)
    common_text = ""
    if common:
        common_text = f"{common[0]}-{common[-1]}周"
    return (
        f"{a.course_name} 与 {b.course_name} 在 {weekdays} "
        f"{a.section_text} 冲突{('（' + common_text + '）') if common_text else ''}"
    )


def detect_conflicts(sessions):
    conflicts = []
    seen = set()
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            a, b = sessions[i], sessions[j]
            if not overlap(a, b):
                continue
            key = tuple(sorted((id(a), id(b))))
            if key in seen:
                continue
            seen.add(key)
            conflicts.append({
                "a": a.course_name,
                "b": b.course_name,
                "weekday": a.weekday,
                "weekday_text": WEEK_NAME.get(a.weekday, ""),
                "section": a.section_text,
                "text": describe_conflict(a, b),
            })
    return conflicts


def sessions_from_selected(rows):
    sessions = []
    for row in rows:
        sessions.extend(parse_course_sessions(
            row.get("courseName") or "",
            row.get("courseNum") or "",
            row.get("teachingTimePlace") or "",
        ))
    return sessions


def candidate_conflicts(candidate_name, candidate_num, candidate_clazz,
                        candidate_text, selected_rows):
    selected_sessions = []
    for row in selected_rows:
        if str(row.get("teachingClassId") or "") == str(candidate_clazz or ""):
            continue
        if candidate_num and str(row.get("courseNum") or "") == str(candidate_num):
            continue
        selected_sessions.extend(parse_course_sessions(
            row.get("courseName") or "",
            row.get("courseNum") or "",
            row.get("teachingTimePlace") or "",
        ))
    if not selected_sessions:
        return []
    candidates = parse_course_sessions(candidate_name, candidate_num, candidate_text)
    result = []
    for candidate in candidates:
        for selected in selected_sessions:
            if overlap(candidate, selected):
                result.append(describe_conflict(candidate, selected))
    return sorted(set(result))


def build_schedule(rows):
    sessions = sessions_from_selected(rows)
    conflicts = detect_conflicts(sessions)
    events = []
    for session in sorted(
        sessions,
        key=lambda s: (s.weekday, s.start_section, s.course_name),
    ):
        events.append({
            "course_name": session.course_name,
            "course_num": session.course_num,
            "teacher": session.teacher,
            "weekday": session.weekday,
            "weekday_text": WEEK_NAME.get(session.weekday, ""),
            "start_section": session.start_section,
            "end_section": session.end_section,
            "section_text": session.section_text,
            "week_text": session.week_text,
            "place": session.place,
        })
    return {"events": events, "conflicts": conflicts}
