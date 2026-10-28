"""Profile and account module constants."""

from datetime import datetime, timezone

# Tokens are short-lived sessions for one local browser.
TOKEN_TTL_SECONDS = 8 * 60 * 60
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
USERNAME_PATTERN = r"^[A-Za-z0-9_]{3,32}$"


def utc_now() -> str:
    """Audit timestamps use UTC, matching the other modules."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
