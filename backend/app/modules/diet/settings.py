"""Diet module configuration. Business dates are not UTC timestamps."""
from datetime import datetime, timezone

# One source of truth; the frontend reads it from /api/diet/config.
BUSINESS_TIME_ZONE = "Asia/Shanghai"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
