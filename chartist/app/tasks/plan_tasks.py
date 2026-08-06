import asyncio
import json
import logging
from datetime import datetime, timezone

import aiohttp
from sqlalchemy import and_, delete, select

from app.config import settings
from app.core.celery_app import celery_app
from app.models.database import SyncSessionLocal
from app.models.history import NotificationLog
from app.models.user import User
from app.utils.plan_utils import (
    get_remaining_time,
    _persian_digits,
)

logger = logging.getLogger(__name__)


# ─── Constants ────────────────────────────────────────────────────────────────

FIRST_THRESHOLD = settings.PLAN_NOTIFICATION_FIRST_RATIO
SECOND_THRESHOLD = settings.PLAN_NOTIFICATION_SECOND_RATIO

NOTIFICATION_FIRST = "first_threshold"
NOTIFICATION_SECOND = "second_threshold"
NOTIFICATION_EXPIRED = "expired"

ACTIVE_STATUSES = ("trial", "active")

# Telegram Bot API base URL
_TG_API = "https://api.telegram.org"

GIFT_DAYS = settings.PLAN_NOTIFICATION_GIFT_DAYS
ANALYSIS_COUNT_DISPLAY_THRESHOLD = settings.PLAN_ANALYSIS_COUNT_DISPLAY_THRESHOLD


def _notification_configuration_error() -> str | None:
    if FIRST_THRESHOLD is None or SECOND_THRESHOLD is None:
        return "notification thresholds are not configured"
    if not 0 < FIRST_THRESHOLD < SECOND_THRESHOLD < 1:
        return "notification thresholds must satisfy 0 < first < second < 1"
    if GIFT_DAYS is None or GIFT_DAYS < 0:
        return "notification gift days are not configured"
    if ANALYSIS_COUNT_DISPLAY_THRESHOLD is None or ANALYSIS_COUNT_DISPLAY_THRESHOLD < 0:
        return "analysis display threshold is not configured"
    return None


# ─── Persian helpers ──────────────────────────────────────────────────────────

def _persian_duration(days: int) -> str:
    """Convert a plan duration in days to a friendly Persian phrase."""
    if days >= 75:
        return "سه ماه"
    if days >= 30:
        return "یک ماه"
    if days >= 7:
        return "یک هفته"
    return "چند روز"


def _analysis_line(count: int) -> str:
    """Build the analysis count line, or '' when the user has too few to mention."""
    if count <= ANALYSIS_COUNT_DISPLAY_THRESHOLD:
        return ""
    return f"  ╺ <b>{_persian_digits(str(count))} تحلیل</b> حرفه‌ای انجام دادی ✨"


# ─── Persian message templates ────────────────────────────────────────────────

def _build_message(
    notification_type: str,
    remaining_time: dict,
    plan_duration_days: int,
    analysis_count: int,
) -> str:
    days_left = remaining_time["days"]
    days_left_str = _persian_digits(str(days_left))
    gift = _persian_digits(str(GIFT_DAYS))
    duration_phrase = _persian_duration(plan_duration_days)
    analysis_block = _analysis_line(analysis_count)

    if notification_type == NOTIFICATION_FIRST:
        analysis_section = f"تا الان:\n{analysis_block}\n\n" if analysis_block else ""
        return (
            "💎 <b>یادآوری پایان طرح</b>\n\n"
            "🌟 سلام رفیق!\n\n"
            f"⏳ فقط <b>{days_left_str} روز</b> دیگه از اشتراکت مونده.\n\n"
            f"{analysis_section}"
            "🎁 اگه قبل از انقضا تمدید کنی،\n"
            f"<b>{gift} روز هدیه</b> می‌گیری! ✨"
        )

    if notification_type == NOTIFICATION_SECOND:
        analysis_section = f"{analysis_block}\n\n" if analysis_block else ""
        return (
            "🔔 <b>فقط چند روز دیگه!</b>\n\n"
            f"⏳ <b>{days_left_str} روز</b> دیگه اشتراکت تموم میشه.\n\n"
            f"📊 توی این <b>{duration_phrase}</b> گذشته:\n"
            f"{analysis_section}"
            f"🎁 الان تمدید کنی ← <b>{gift} روز هدیه</b> می‌گیری! 💎"
        )

    # expired
    count_str = _persian_digits(str(analysis_count))
    if analysis_block:
        companionship = (
            f"🌹 این <b>{duration_phrase}</b> همراه ما بودی و "
            f"<b>{count_str} تحلیل حرفه‌ای</b> انجام دادی. "
            f"ممنون که اعتماد کردی 🙏"
        )
    else:
        companionship = (
            f"🌹 ممنون که این <b>{duration_phrase}</b> همراه ما بودی 🙏"
        )
    return (
        "💝 <b>امروز آخرین روز اشتراکته</b>\n\n"
        f"{companionship}\n\n"
        "🚀 هر وقت آماده شدی، تمدید یه کلیکه.\n"
        "✨ هنوز می‌تونی بدون وقفه ادامه بدی."
    )


def _build_keyboard(notification_type: str) -> dict:
    """Inline keyboard with the 'show_subscription' button the bot already handles."""
    if notification_type == NOTIFICATION_SECOND:
        label = f"🎁 تمدید با {GIFT_DAYS} روز هدیه"
    elif notification_type == NOTIFICATION_EXPIRED:
        label = "💎 تمدید اشتراک + هدیه"
    else:
        label = "✨ تمدید اشتراک"
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": "show_subscription"}]
        ]
    }


# ─── Telegram send helper ─────────────────────────────────────────────────────

async def _telegram_send(user_id: int, text: str, reply_markup: dict) -> bool:
    """Send a single message via the Bot HTTP API. Returns True on success."""
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not configured; cannot send plan notification")
        return False

    url = f"{_TG_API}/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup),
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return True
                body = await resp.text()
                logger.warning(
                    f"Telegram sendMessage failed for {user_id}: "
                    f"status={resp.status} body={body[:300]}"
                )
                return False
    except Exception as e:
        logger.error(f"Telegram sendMessage exception for {user_id}: {e}")
        return False


async def _send_pending(
    user_id: int,
    notif_type: str,
    remaining_time: dict,
    plan_duration_days: int,
    analysis_count: int,
) -> bool:
    """Build and send a single notification. Returns True if delivered."""
    text = _build_message(notif_type, remaining_time, plan_duration_days, analysis_count)
    keyboard = _build_keyboard(notif_type)
    return await _telegram_send(user_id, text, keyboard)


# ─── Main Celery task ─────────────────────────────────────────────────────────

@celery_app.task(name='check_expiring_plans')
def check_expiring_plans():
    """
    Detect users whose plan has reached the configured or expired thresholds
    and send a Telegram reminder to each one (once per period).
    Runs every 3 hours via Celery Beat.
    """
    logger.info("=== CHECKING EXPIRING PLANS ===")

    configuration_error = _notification_configuration_error()
    if configuration_error:
        logger.error("Plan notifications disabled: %s", configuration_error)
        return

    # Collect work first (sync session), then send (async) outside the session.
    to_notify: list[dict] = []

    try:
        with SyncSessionLocal() as db:
            now = datetime.now(timezone.utc)

            candidates = db.execute(
                select(User).where(
                    and_(
                        User.plan_end_date.isnot(None),
                        User.plan_updated_at.isnot(None),
                        User.plan_status.in_(ACTIVE_STATUSES),
                    )
                )
            ).scalars().all()

            for user in candidates:
                plan_start = user.plan_updated_at
                plan_end = user.plan_end_date

                if plan_start.tzinfo is None:
                    plan_start = plan_start.replace(tzinfo=timezone.utc)
                if plan_end.tzinfo is None:
                    plan_end = plan_end.replace(tzinfo=timezone.utc)

                total_seconds = (plan_end - plan_start).total_seconds()
                if total_seconds <= 0:
                    continue

                elapsed = (now - plan_start).total_seconds()
                ratio = elapsed / total_seconds

                # Figure out which threshold (if any) we crossed for this user
                target_type: str | None = None
                if ratio >= 1.0:
                    target_type = NOTIFICATION_EXPIRED
                elif ratio >= SECOND_THRESHOLD:
                    target_type = NOTIFICATION_SECOND
                elif ratio >= FIRST_THRESHOLD:
                    target_type = NOTIFICATION_FIRST

                if target_type is None:
                    continue

                # Dedup: have we already logged this notification for the current period?
                already = db.execute(
                    select(NotificationLog).where(
                        and_(
                            NotificationLog.user_id == user.id,
                            NotificationLog.notification_type == target_type,
                        )
                    )
                ).scalar_one_or_none()

                if already:
                    continue

                remaining_time = get_remaining_time(plan_end)
                plan_duration_days = int(total_seconds // 86400)
                to_notify.append({
                    "user_id": user.id,
                    "type": target_type,
                    "remaining_time": remaining_time,
                    "plan_duration_days": plan_duration_days,
                    "analysis_count": int(user.total_requests or 0),
                    "ratio": ratio,
                    "plan_end": plan_end,
                })

            # Mark expired users + persist notification logs inside the same session
            for item in to_notify:
                if item["type"] == NOTIFICATION_EXPIRED:
                    user = db.get(User, item["user_id"])
                    if user is not None:
                        user.plan_status = "expired"
                db.add(NotificationLog(
                    user_id=item["user_id"],
                    notification_type=item["type"],
                ))

            db.commit()

    except Exception as e:
        logger.error(f"Error in check_expiring_plans DB phase: {e}")
        logger.exception(e)
        return

    # ── Async send phase (outside DB session) ────────────────────────────────
    if not to_notify:
        logger.info("=== NO USERS TO NOTIFY ===")
        return

    async def _dispatch_all():
        sent = 0
        for item in to_notify:
            ok = await _send_pending(
                item["user_id"],
                item["type"],
                item["remaining_time"],
                item["plan_duration_days"],
                item["analysis_count"],
            )
            if ok:
                sent += 1
            # Telegram global rate limit: stay well under 30 msg/sec
            await asyncio.sleep(0.05)
        return sent

    try:
        sent_count = asyncio.run(_dispatch_all())
        logger.info(
            f"=== EXPIRING PLANS CHECK COMPLETE: "
            f"queued={len(to_notify)} sent={sent_count} ==="
        )
    except Exception as e:
        logger.error(f"Error in check_expiring_plans send phase: {e}")
        logger.exception(e)
