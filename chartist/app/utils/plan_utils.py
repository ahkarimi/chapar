from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

def get_valid_plan_packages() -> tuple[int, ...]:
    """Return positive plan durations configured by the operator."""
    packages = []
    for value in settings.PLAN_PACKAGES_DAYS.split(","):
        value = value.strip()
        if value:
            days = int(value)
            if days > 0 and days not in packages:
                packages.append(days)
    return tuple(packages)


# Initialize jdatetime for Persian date formatting
try:
    import jdatetime
    _JDATETIME_AVAILABLE = True
except ImportError:
    _JDATETIME_AVAILABLE = False
    logger.warning("jdatetime not available. Persian date formatting will fall back to Gregorian.")


def _now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def has_active_plan(plan_end_date: Optional[datetime]) -> bool:
    """Check if user has an active plan (plan_end_date is in the future)."""
    if plan_end_date is None:
        return False
    return plan_end_date > _now()


def get_remaining_days(plan_end_date: Optional[datetime]) -> int:
    """Get remaining days of the plan. Returns 0 if expired or no plan."""
    if plan_end_date is None:
        return 0
    now = _now()
    if plan_end_date <= now:
        return 0
    return (plan_end_date - now).days


def get_remaining_time(plan_end_date: Optional[datetime]) -> dict:
    """
    Get remaining time of the plan in days, hours, minutes.
    Returns a dict with full breakdown for precise time display.
    Returns all zeros if expired or no plan.
    """
    if plan_end_date is None:
        return {"days": 0, "hours": 0, "minutes": 0, "total_seconds": 0}
    now = _now()
    if plan_end_date <= now:
        return {"days": 0, "hours": 0, "minutes": 0, "total_seconds": 0}

    delta = plan_end_date - now
    total_seconds = int(delta.total_seconds())
    days = delta.days
    hours, remainder = divmod(total_seconds - days * 86400, 3600)
    minutes = remainder // 60

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "total_seconds": total_seconds,
    }


def get_remaining_time_human(plan_end_date: Optional[datetime]) -> str:
    """
    Get human-readable remaining time in Persian.
    Examples:
        - "۵ روز و ۳ ساعت و ۱۰ دقیقه"
        - "۲ ساعت و ۳۰ دقیقه"
        - "۱۵ دقیقه"
        - "منقضی شده"
    """
    remaining = get_remaining_time(plan_end_date)
    if remaining["total_seconds"] <= 0:
        return "منقضی شده"

    parts = []
    if remaining["days"] > 0:
        parts.append(f"{remaining['days']} روز")
    if remaining["hours"] > 0:
        parts.append(f"{remaining['hours']} ساعت")
    if remaining["minutes"] > 0:
        parts.append(f"{remaining['minutes']} دقیقه")

    if not parts:
        return "کمتر از یک دقیقه"

    return " و ".join(parts)


def _persian_digits(text: str) -> str:
    """Convert Western digits to Persian digits."""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(
        persian_digits[int(c)] if c.isdigit() else c for c in text
    )


def format_datetime_human(dt: Optional[datetime]) -> str:
    """
    Format a datetime to a human-readable Persian (Jalali) string.
    Falls back to Gregorian if jdatetime is not available.
    """
    if dt is None:
        return "نامشخص"

    # Ensure we have a timezone-aware datetime in local/UTC context
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if _JDATETIME_AVAILABLE:
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=dt)
            formatted = jd.strftime("%Y/%m/%d %H:%M")
            return _persian_digits(formatted)
        except Exception as e:
            logger.warning(f"Error converting to Persian date: {e}")

    # Fallback to Gregorian
    formatted = dt.strftime("%Y-%m-%d %H:%M")
    return _persian_digits(formatted)


def format_date_human(dt: Optional[datetime]) -> str:
    """
    Format a datetime to a human-readable Persian (Jalali) date string (no time).
    """
    if dt is None:
        return "نامشخص"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if _JDATETIME_AVAILABLE:
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=dt)
            formatted = jd.strftime("%Y/%m/%d")
            return _persian_digits(formatted)
        except Exception as e:
            logger.warning(f"Error converting to Persian date: {e}")

    formatted = dt.strftime("%Y-%m-%d")
    return _persian_digits(formatted)


def get_plan_status(plan_end_date: Optional[datetime], current_status: str = "trial") -> str:
    """
    Get the current plan status based on end date.
    Returns: "trial", "active", or "expired"
    """
    if plan_end_date is None:
        return "expired"

    if has_active_plan(plan_end_date):
        return current_status if current_status in ("trial", "active") else "active"
    else:
        return "expired"


def add_days_to_plan(current_end_date: Optional[datetime], days: int) -> datetime:
    """
    Add days to the current plan.
    If plan is expired or None, start from now.
    If plan is active, extend from current end date.
    """
    now = _now()

    if current_end_date is None or current_end_date <= now:
        # Plan is expired or doesn't exist - start fresh from now
        return now + timedelta(days=days)
    else:
        # Plan is active - extend from current end date
        return current_end_date + timedelta(days=days)


def is_valid_package(days: int) -> bool:
    """Check if the given duration is configured as a plan package."""
    return days in get_valid_plan_packages()


def get_plan_summary(plan_end_date: Optional[datetime], current_status: str = "trial") -> dict:
    """Get a summary of the user's plan for API responses."""
    remaining = get_remaining_days(plan_end_date)
    status = get_plan_status(plan_end_date, current_status)

    return {
        "plan_status": status,
        "plan_end_date": plan_end_date.isoformat() if plan_end_date else None,
        "plan_end_date_human": format_datetime_human(plan_end_date),
        "remaining_days": remaining,
        "remaining_time_human": get_remaining_time_human(plan_end_date),
        "is_active": has_active_plan(plan_end_date),
    }
