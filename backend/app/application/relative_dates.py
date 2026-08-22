"""Asia/Shanghai 相对日期首次解析与固定。"""
import calendar
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")

_ZH_NUMBERS = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def shanghai_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(SHANGHAI)


def resolve_relative_date(text: str, reference: datetime | None = None) -> dict:
    ref = reference or shanghai_now()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=SHANGHAI)
    else:
        ref = ref.astimezone(SHANGHAI)
    base = ref.date()
    expression = "今天"
    absolute = base

    explicit = re.search(r"(?<!\d)(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text)
    if explicit:
        expression = explicit.group(0)
        absolute = date(int(explicit.group(1)), int(explicit.group(2)), int(explicit.group(3)))
    elif "昨天" in text:
        expression, absolute = "昨天", base - timedelta(days=1)
    elif "前天" in text:
        expression, absolute = "前天", base - timedelta(days=2)
    elif "明天" in text:
        expression, absolute = "明天", base + timedelta(days=1)
    elif "后天" in text:
        expression, absolute = "后天", base + timedelta(days=2)
    elif "月底" in text:
        expression = "月底"
        absolute = date(base.year, base.month, calendar.monthrange(base.year, base.month)[1])
    else:
        match = re.search(r"([1-9]\d?|[一二两三四五六七八九十])天后", text)
        if match:
            raw = match.group(1)
            days = int(raw) if raw.isdigit() else _ZH_NUMBERS[raw]
            expression, absolute = match.group(0), base + timedelta(days=days)

    return {
        "expression": expression,
        "date": absolute.isoformat(),
        "timezone": "Asia/Shanghai",
        "resolved_at": ref.isoformat(),
    }
