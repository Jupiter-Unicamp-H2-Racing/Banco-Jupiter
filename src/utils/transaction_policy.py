from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from errors import InvalidParameter


def validate_idempotency_key(value: str | None) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 255):
        raise InvalidParameter(
            "Idempotency-Key must contain 1 to 255 characters and cannot consist only of whitespace."
        )


def monthly_window(now: datetime, timezone_name: str) -> tuple[datetime, datetime]:
    local_now = now.astimezone(ZoneInfo(timezone_name))
    local_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if local_start.month == 12:
        local_end = local_start.replace(year=local_start.year + 1, month=1)
    else:
        local_end = local_start.replace(month=local_start.month + 1)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
