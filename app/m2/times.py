"""M2 的时间口径：库里统一存 UTC，页面用 Asia/Shanghai；只接受整点小时。

任务书要求「以整点小时为单位、单次最多 4 小时」，这里把规则集中在一处，
路由层只负责把 ValueError 转成 422，避免各接口各写一套判断。
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("Asia/Shanghai")
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

MIN_HOURS = 1
MAX_HOURS = 4
OPEN_HOUR = 7  # 本地时间最早可开始
CLOSE_HOUR = 22  # 本地时间最晚结束（不含该小时之后的时段）


class InvalidPeriod(ValueError):
    """时段不合法，调用方转成 422。"""


def parse_moment(raw: str) -> datetime:
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError as error:
        raise InvalidPeriod("时间格式应为 ISO 8601，例如 2026-10-22T09:00:00+08:00") from error
    if moment.tzinfo is None:
        raise InvalidPeriod("时间必须带时区偏移，例如 +08:00 或 Z")
    return moment


def to_utc_text(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(UTC_FORMAT)


def parse_period(start_raw: str, end_raw: str, now: datetime | None = None) -> tuple[str, str, int]:
    """校验整点、时长与开放时间，返回 (UTC 开始, UTC 结束, 小时数)。"""
    start = parse_moment(start_raw).astimezone(LOCAL_ZONE)
    end = parse_moment(end_raw).astimezone(LOCAL_ZONE)
    if end <= start:
        raise InvalidPeriod("结束时间必须晚于开始时间")
    if start.minute or start.second or end.minute or end.second:
        raise InvalidPeriod("借用必须按整点小时提交，如 09:00–11:00")
    if start.date() != end.date():
        raise InvalidPeriod("暂不支持跨天借用")
    hours = int((end - start).total_seconds() // 3600)
    if hours < MIN_HOURS:
        raise InvalidPeriod("借用时长至少 1 小时")
    if hours > MAX_HOURS:
        raise InvalidPeriod(f"单次最多借用 {MAX_HOURS} 小时")
    if start.hour < OPEN_HOUR or end.hour > CLOSE_HOUR:
        raise InvalidPeriod(f"可借用时间为 {OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00")
    if start <= (now or datetime.now(timezone.utc)).astimezone(LOCAL_ZONE):
        raise InvalidPeriod("开始时间必须晚于当前时间")
    return to_utc_text(start), to_utc_text(end), hours
