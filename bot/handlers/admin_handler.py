import logging
import re

from telegram import (
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from constants import PLAN_PACKAGES_DAYS
from keyboards import AdminKeyboard, UserKeyboard
from localization import is_button
from .broadcast import BroadcastMixin

logger = logging.getLogger(__name__)


class AdminHandler(BroadcastMixin):
    """Handler for admin commands."""

    def __init__(self, user_db, settings_db, api_request):
        """Initialize with database and API clients.

        Args:
            user_db: User database handler
            settings_db: Settings database handler
            api_request: API request handler
        """
        self.user = user_db
        self.settings = settings_db
        self.api_request = api_request
        self.start_time = None

    def set_start_time(self, start_time):
        """Set bot start time."""
        self.start_time = start_time

    # ──────────────────────────────────────────────────────────────────────────
    #  Broadcast helpers
    # ──────────────────────────────────────────────────────────────────────────







    # ──────────────────────────────────────────────────────────────────────────
    #  Main admin message handler
    # ──────────────────────────────────────────────────────────────────────────

    async def handle_admin_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle incoming messages from admin users."""
        # Drop messages that arrived before the bot started
        if update.message.date.timestamp() < self.start_time:
            return

        # text may be None when the admin sends a photo / video
        text = update.message.text
        sender_id = update.effective_user.id

        if not self.settings.is_admin(sender_id):
            return

        user = await self.user.get_user(sender_id)
        state = user["State"]
        language = user.get("Language") or "fa"

        # ── Admin panel entry ─────────────────────────────────────────────────
        if is_button(text, "admin"):
            await self.user.set_state(sender_id, "admin")
            await update.message.reply_text(
                text="پنل مدیریت:",
                reply_markup=AdminKeyboard.main(),
            )
            return

        # ── Back button ───────────────────────────────────────────────────────
        elif is_button(text, "back"):
            if state in ("admin", "get_user_info"):
                await self.user.set_state(sender_id, "")
                await update.message.reply_text(
                    text="به پنل کاربر بازگشتیم.",
                    reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
                )
            elif state in [
                "set_toobit_invitation_link",
                "set_toobit_invitation_code",
                "force_join",
                "add_force_join",
                "admin_force_join_remove_channel",
                "add_admin",
                "remove_admin",
                "set_help_text",
                "set_help_video",
                "set_increase_credit_text",
                "set_prize_text",
                "set_dollar_analysis_text",
                "set_gold_analysis_text",
                "add_plan_time",
                "add_plan_time_amount",
                "settings",
                # broadcast sub-states
                "broadcast_start",
                "broadcast_text",
                "broadcast_media",
                "broadcast_button_text",
                "broadcast_button_link",
                "broadcast_confirm",
            ]:
                context.user_data.pop("broadcast_draft", None)  # clear any draft
                await self.user.set_state(sender_id, "admin")
                await update.message.reply_text(
                    text="به پنل مدیریت بازگشتیم.",
                    reply_markup=AdminKeyboard.main(),
                )

        # ── Add plan time: entry ──────────────────────────────────────────────
        elif text == "• افزودن زمان به کاربر •" and state == "admin":
            await self.user.set_state(sender_id, "add_plan_time")
            await update.message.reply_text(
                text="آیدی کاربر را برای افزودن زمان وارد کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        # ── Add plan time: receive user ID ────────────────────────────────────
        elif state == "add_plan_time":
            try:
                user_id = int(text)
                user_info = await self.api_request.me(user_id)

                if not user_info or user_info.get("error"):
                    await update.message.reply_text(
                        "کاربر یافت نشد. لطفا آیدی معتبر وارد کنید."
                    )
                    return

                await self.user.set_state(sender_id, "add_plan_time_amount")

                if not hasattr(context, "user_data"):
                    context.user_data = {}

                context.user_data["target_user_id"] = user_id
                context.user_data["target_user_name"] = user_info.get("name", "Unknown")

                plan_status = user_info.get("plan_status", "unknown")
                remaining_time_human = user_info.get("remaining_time_human", "۰ روز")
                plan_end_date_human = user_info.get("plan_end_date_human", "نامشخص")

                msg = (
                    f"کاربر یافت شد:\n"
                    f"👤 نام: {user_info.get('name', 'Unknown')}\n"
                    f"🆔 آیدی: {user_id}\n"
                    f"⏳ وضعیت طرح: {plan_status}\n"
                    f"🕒 زمان باقی‌مانده: {remaining_time_human}\n"
                    f"📅 تاریخ پایان: {plan_end_date_human}\n\n"
                    f"لطفاً یکی از بسته‌های زمانی زیر را انتخاب کنید:"
                )
                await update.message.reply_text(
                    text=msg, reply_markup=AdminKeyboard.plan_packages()
                )
            except ValueError:
                await update.message.reply_text(
                    "لطفا یک آیدی معتبر (عددی) وارد کنید."
                )
            except Exception as e:
                logger.error(f"Error processing user ID for plan time add: {e}")
                await update.message.reply_text(
                    "خطایی رخ داد. لطفا دوباره تلاش کنید."
                )

        # ── Add plan time: receive package ────────────────────────────────────
        elif state == "add_plan_time_amount":
            try:
                package_text = text.strip()
                if not package_text.startswith("+"):
                    await update.message.reply_text(
                        "لطفاً یکی از بسته‌های زمانی معتبر را انتخاب کنید."
                    )
                    return

                match = re.search(r"\+?(\d+)", package_text)
                if not match:
                    await update.message.reply_text(
                        "لطفاً یکی از بسته‌های زمانی معتبر را انتخاب کنید."
                    )
                    return

                package_days = int(match.group(1))
                if package_days not in PLAN_PACKAGES_DAYS:
                    await update.message.reply_text(
                        f"بسته نامعتبر. بسته‌های مجاز: {PLAN_PACKAGES_DAYS}"
                    )
                    return

                if (
                    not hasattr(context, "user_data")
                    or "target_user_id" not in context.user_data
                ):
                    await update.message.reply_text(
                        "خطا: اطلاعات کاربر یافت نشد. لطفا دوباره تلاش کنید."
                    )
                    await self.user.set_state(sender_id, "admin")
                    await update.message.reply_text(
                        text="به پنل مدیریت بازگشتیم.",
                        reply_markup=AdminKeyboard.main(),
                    )
                    return

                target_user_id = context.user_data["target_user_id"]
                target_user_name = context.user_data.get("target_user_name", "Unknown")

                result = await self.api_request.add_plan_time(
                    target_user_id, package_days
                )
                await self.user.set_state(sender_id, "admin")

                if result.get("error"):
                    await update.message.reply_text(
                        text=f"خطا در افزودن زمان: {result.get('message', 'خطای نامشخص')}",
                        reply_markup=AdminKeyboard.main(),
                    )
                    return

                new_plan_end_date_human = result.get(
                    "new_plan_end_date_human", "نامشخص"
                )
                remaining_time_human = result.get("remaining_time_human", "۰ روز")

                await update.message.reply_text(
                    text=(
                        f"✅ زمان طرح کاربر با موفقیت افزوده شد!\n\n"
                        f"👤 نام: {target_user_name}\n"
                        f"🆔 آیدی: {target_user_id}\n"
                        f"➕ روزهای افزوده شده: {package_days} روز\n"
                        f"📅 تاریخ پایان جدید: {new_plan_end_date_human}\n"
                        f"🕒 زمان باقی‌مانده: {remaining_time_human}"
                    ),
                    reply_markup=AdminKeyboard.main(),
                )

                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            f"✨ تبریک! {package_days} روز به طرح شما افزوده شد.\n"
                            f"📅 تاریخ پایان طرح شما: {new_plan_end_date_human}\n"
                            f"🕒 زمان باقی‌مانده: {remaining_time_human}"
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error notifying user about plan time add: {e}")

            except Exception as e:
                logger.error(f"Error adding plan time: {e}")
                await update.message.reply_text("خطایی رخ داد. لطفا دوباره تلاش کنید.")
                await self.user.set_state(sender_id, "admin")
                await update.message.reply_text(
                    text="به پنل مدیریت بازگشتیم.",
                    reply_markup=AdminKeyboard.main(),
                )

        # ── User info: entry ──────────────────────────────────────────────────
        elif text == "• دریافت اطلاعات کاربر •" and state == "admin":
            await self.user.set_state(sender_id, "get_user_info")
            await update.message.reply_text(
                text="آیدی عددی کاربر یا یوزرنیم (با یا بدون @) را ارسال کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        # ── User info: receive user ID ────────────────────────────────────────
        elif state == "get_user_info":
            try:
                text = text.strip()
                if text.isdigit():
                    user_id = int(text)
                else:
                    # It's a username (with or without @)
                    username = text.lstrip("@")

                    # 1. Try to find in our database (case-insensitive)
                    user_by_username = await self.api_request.get_user_by_username(username)
                    if user_by_username and not user_by_username.get("error"):
                        user_id = user_by_username["id"]
                    else:
                        # 2. Fallback: Try Telegram Bot API
                        try:
                            chat = await context.bot.get_chat(f"@{username}")
                            user_id = chat.id
                        except BadRequest:
                            await update.message.reply_text(
                                "کاربر یافت نشد. لطفاً یک آیدی یا یوزرنیم معتبر وارد کنید."
                            )
                            return

                user_info = await self.api_request.me(user_id)

                if not user_info or user_info.get("error"):
                    await update.message.reply_text(
                        "کاربر یافت نشد. لطفا آیدی معتبر وارد کنید."
                    )
                    return

                from html import escape

                def e(val):
                    """Escape HTML special characters in user-provided text."""
                    return escape(str(val)) if val is not None else ""

                msg = f"👤 <b>نام</b>: {e(user_info.get('name'))}\n"
                msg += f"🆔 <b>آیدی</b>: {user_info['id']}\n"

                if user_info.get("email"):
                    msg += f"📧 <b>ایمیل</b>: {e(user_info['email'])}\n"
                if user_info.get("phone_number"):
                    msg += f"📞 <b>شماره تلفن</b>: {e(user_info['phone_number'])}\n"
                if user_info.get("telegram_username"):
                    msg += f"🆔 <b>یوزرنیم تلگرام</b>: @{e(user_info['telegram_username'])}\n"

                msg += f"📊 <b>تعداد درخواست ها</b>: {user_info['total_requests']}\n"

                plan_status = user_info.get("plan_status", "unknown")
                remaining_time_human = user_info.get("remaining_time_human", "۰ روز")
                plan_end_date_human = user_info.get("plan_end_date_human", "نامشخص")

                status_map = {
                    "trial": "⏳ <b>وضعیت طرح</b>: آزمایشی\n",
                    "active": "✅ <b>وضعیت طرح</b>: فعال\n",
                    "expired": "❌ <b>وضعیت طرح</b>: منقضی شده\n",
                }
                msg += status_map.get(
                    plan_status, f"❓ <b>وضعیت طرح</b>: {e(plan_status)}\n"
                )

                if plan_end_date_human and plan_end_date_human != "نامشخص":
                    msg += f"📅 <b>تاریخ پایان طرح</b>: {e(plan_end_date_human)}\n"
                msg += f"🕒 <b>زمان باقی‌مانده</b>: {e(remaining_time_human)}\n"

                # Fetch and display plan history
                plan_history = await self.api_request.get_user_plan_history(user_id)
                if plan_history and not plan_history.get("error"):
                    total_purchases = plan_history.get("total_purchases", 0)
                    unique_plans = plan_history.get("unique_plans", [])

                    msg += f"\n📦 <b>تاریخچه خرید طرح‌ها</b>\n"
                    msg += f"🔢 <b>تعداد کل خریدها</b>: {total_purchases}\n"

                    if unique_plans:
                        plans_str = "، ".join(f"+{days} روز" for days in unique_plans)
                        msg += f"📋 <b>طرح‌های خریداری‌شده</b>: {plans_str}\n"

                    history_list = plan_history.get("history", [])
                    if history_list:
                        msg += f"\n📝 <b>آخرین خریدها</b>:\n"
                        for idx, h in enumerate(history_list[:5], start=1):
                            days = h.get("days_added", "?")
                            date_str = h.get("created_at_human", "نامشخص")
                            msg += f"  {idx}. +{days} روز – {e(date_str)}\n"

                await update.message.reply_text(
                    text=msg, parse_mode=ParseMode.HTML
                )
                await self.user.set_state(sender_id, "admin")
                await update.message.reply_text(
                    text="به پنل مدیریت بازگشتیم.",
                    reply_markup=AdminKeyboard.main(),
                )
            except ValueError:
                await update.message.reply_text(
                    "لطفا یک آیدی عددی معتبر وارد کنید."
                )
            except Exception as e:
                logger.error(f"Error getting user info: {e}")
                await update.message.reply_text(
                    "خطایی رخ داد هنگام دریافت اطلاعات کاربر. لطفا دوباره تلاش کنید."
                )

        # ── Set help text ─────────────────────────────────────────────────────
        elif text == "• تنظیم متن راهنما •" and state == "admin":
            self.user.set_state(sender_id, "set_help_text")
            await update.message.reply_text(
                text="متن راهنما را ارسال کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        elif state == "set_help_text":
            self.settings.set_help_text(text)
            self.user.set_state(sender_id, "admin")
            await update.message.reply_text(
                text="متن راهنما تنظیم شد.",
                reply_markup=AdminKeyboard.main(),
            )

        # ── Set help video ────────────────────────────────────────────────────
        elif text == "• تنظیم ویدیو راهنما •" and state == "admin":
            self.user.set_state(sender_id, "set_help_video")
            await update.message.reply_text(
                text="ویدیو راهنما را ارسال کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        elif state == "set_help_video":
            if not update.message.video:
                await update.message.reply_text("لطفا ویدیو را ارسال کنید.")
                return
            file_id = update.message.video.file_id
            self.settings.set_help_video(file_id)
            self.user.set_state(sender_id, "admin")
            await update.message.reply_text(
                text="ویدیو راهنما تنظیم شد.",
                reply_markup=AdminKeyboard.main(),
            )

        # ── Set increase-credit text ──────────────────────────────────────────
        elif text == "• تظیم متن افزایش اعتبار •" and state == "admin":
            self.user.set_state(sender_id, "set_increase_credit_text")
            await update.message.reply_text(
                text="متن افزایش اعتبار را ارسال کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        elif state == "set_increase_credit_text":
            self.settings.set_increase_credit_text(text)
            self.user.set_state(sender_id, "admin")
            await update.message.reply_text(
                text="متن افزایش اعتبار تنظیم شد.",
                reply_markup=AdminKeyboard.main(),
            )

        elif text == "• تنظیم متن جایزه •" and state == "admin":
            self.user.set_state(sender_id, "set_prize_text")
            await update.message.reply_text(
                text="متن جایزه را ارسال کنید:",
                reply_markup=AdminKeyboard.back(),
            )

        elif state == "set_prize_text":
            self.settings.set_prize_text(text)
            self.user.set_state(sender_id, "admin")
            await update.message.reply_text(
                text="متن جایزه تنظیم شد.",
                reply_markup=AdminKeyboard.main(),
            )

        # ══════════════════════════════════════════════════════════════════════
        #  BROADCAST  –  multi-step wizard
        # ══════════════════════════════════════════════════════════════════════

        # Step 0 – entry: admin taps the broadcast button
        elif text == "• ارسال پیام همگانی •" and state == "admin":
            await self.user.set_state(sender_id, "broadcast_start")
            context.user_data["broadcast_draft"] = {}
            await update.message.reply_text(
                text="📢 نوع پیام همگانی را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(
                    [["📝 پیام متنی", "🖼 پیام مولتی‌مدیا"], ["• برگشت •"]],
                    resize_keyboard=True,
                ),
            )

        # Step 1 – choose type
        elif state == "broadcast_start":
            if text == "📝 پیام متنی":
                context.user_data["broadcast_draft"]["type"] = "text"
                await self.user.set_state(sender_id, "broadcast_text")
                await update.message.reply_text(
                    text=(
                        "✍️ متن پیام خود را بنویسید.\n\n"
                        "<b>قالب‌بندی پشتیبانی‌شده:</b>\n"
                        "• <code>**متن**</code>  ←  بولد\n"
                        "• <code>_متن_</code>  ←  ایتالیک\n"
                        "• <code>[عنوان](https://...)</code>  ←  لینک\n\n"
                        "تگ‌های HTML مستقیم مثل <code>&lt;b&gt;</code> هم پذیرفته می‌شوند."
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=AdminKeyboard.back(),
                )

            elif text == "🖼 پیام مولتی‌مدیا":
                context.user_data["broadcast_draft"]["type"] = "media"
                await self.user.set_state(sender_id, "broadcast_media")
                await update.message.reply_text(
                    text=(
                        "📸 تصویر یا ویدیوی خود را ارسال کنید.\n\n"
                        "کپشن (اختیاری) هم می‌توانید اضافه کنید.\n"
                        "قالب‌بندی کپشن:\n"
                        "• <code>**متن**</code>  ←  بولد\n"
                        "• <code>[عنوان](https://...)</code>  ←  لینک"
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=AdminKeyboard.back(),
                )

        # Step 2a – receive plain text
        elif state == "broadcast_text":
            if not text:
                await update.message.reply_text("⚠️ لطفاً متن پیام را وارد کنید.")
                return

            context.user_data["broadcast_draft"]["text"] = self._format_message_text(
                text
            )
            await self.user.set_state(sender_id, "broadcast_button_text")
            await update.message.reply_text(
                text="✅ متن دریافت شد.\n\n🔘 حالا <b>متن دکمه</b> اینلاین را وارد کنید:",
                parse_mode=ParseMode.HTML,
                reply_markup=AdminKeyboard.back(),
            )

        # Step 2b – receive photo or video
        elif state == "broadcast_media":
            if update.message.photo:
                file_id = update.message.photo[-1].file_id  # largest available size
                media_type = "photo"
            elif update.message.video:
                file_id = update.message.video.file_id
                media_type = "video"
            else:
                await update.message.reply_text(
                    "⚠️ لطفاً یک تصویر یا ویدیو ارسال کنید."
                )
                return

            raw_caption = update.message.caption or ""
            context.user_data["broadcast_draft"].update(
                {
                    "file_id": file_id,
                    "media_type": media_type,
                    "caption": (
                        self._format_message_text(raw_caption) if raw_caption else ""
                    ),
                }
            )

            await self.user.set_state(sender_id, "broadcast_button_text")
            await update.message.reply_text(
                text="✅ رسانه دریافت شد.\n\n🔘 حالا <b>متن دکمه</b> اینلاین را وارد کنید:",
                parse_mode=ParseMode.HTML,
                reply_markup=AdminKeyboard.back(),
            )

        # Step 3 – button label
        elif state == "broadcast_button_text":
            if not text:
                await update.message.reply_text("⚠️ لطفاً متن دکمه را وارد کنید.")
                return

            context.user_data["broadcast_draft"]["button_text"] = text
            await self.user.set_state(sender_id, "broadcast_button_link")
            await update.message.reply_text(
                text=(
                    "🔗 لینک دکمه را وارد کنید.\n\n"
                    "برای دکمه پیش‌فرض (راه‌اندازی ربات مثل /start) "
                    "کلمه <b>پیش‌فرض</b> را بزنید."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=AdminKeyboard.back(),
            )

        # Step 4 – button link → build preview → ask for confirmation
        elif state == "broadcast_button_link":
            if not text:
                await update.message.reply_text(
                    '⚠️ لینک را وارد کنید یا "پیش‌فرض" بزنید.'
                )
                return

            cleaned = text.strip()
            if cleaned in ("پیش‌فرض", "default", "پیش فرض"):
                button_link = f"https://t.me/{context.bot.username}?start=main"
            elif cleaned.startswith(("http://", "https://", "t.me/")):
                button_link = cleaned
                if button_link.startswith("t.me/"):
                    button_link = "https://" + button_link
            else:
                await update.message.reply_text(
                    "⚠️ لینک نامعتبر.\n"
                    "لینک باید با <code>https://</code> یا <code>t.me/</code> شروع شود،\n"
                    "یا کلمه <b>پیش‌فرض</b> را بزنید.",
                    parse_mode=ParseMode.HTML,
                )
                return

            draft = context.user_data["broadcast_draft"]
            draft["button_link"] = button_link

            await self.user.set_state(sender_id, "broadcast_confirm")

            # ── Preview ────────────────────────────────────────────────
            keyboard = self._build_broadcast_keyboard(draft["button_text"], button_link)
            await update.message.reply_text(
                "👁 <b>پیش‌نمایش پیام همگانی:</b>",
                parse_mode=ParseMode.HTML,
            )
            try:
                await self._send_broadcast_to_user(
                    context.bot, sender_id, draft, keyboard
                )
            except Exception as e:
                logger.error(f"Broadcast preview error: {e}")
                await update.message.reply_text(
                    "⚠️ خطا در نمایش پیش‌نمایش. لطفاً دوباره تلاش کنید."
                )
                return

            all_users = await self.user.get_all_users()
            total_count = len(all_users)

            await update.message.reply_text(
                text=(
                    f"آیا از ارسال این پیام به <b>{total_count}</b> کاربر مطمئن هستید؟"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardMarkup(
                    [["✅ بله، ارسال کن", "❌ لغو"]],
                    resize_keyboard=True,
                ),
            )

        # Step 5 – confirm or cancel
        elif state == "broadcast_confirm":
            if text == "✅ بله، ارسال کن":
                draft = context.user_data.get("broadcast_draft")
                if not draft:
                    await update.message.reply_text(
                        "⚠️ اطلاعات پیام یافت نشد. لطفاً دوباره شروع کنید."
                    )
                    await self.user.set_state(sender_id, "admin")
                    await update.message.reply_text(
                        text="به پنل مدیریت بازگشتیم.",
                        reply_markup=AdminKeyboard.main(),
                    )
                    return

                await self.user.set_state(sender_id, "admin")
                total_users = await self.broadcast_message(draft, context.bot)
                context.user_data.pop("broadcast_draft", None)

                if total_users > 0:
                    await update.message.reply_text(
                        text=(
                            f"✅ پیام به <b>{total_users}</b> کاربر در صف ارسال قرار گرفت.\n"
                            f"گزارش کامل پس از اتمام ارسال به شما اطلاع داده خواهد شد."
                        ),
                        parse_mode=ParseMode.HTML,
                        reply_markup=AdminKeyboard.main(),
                    )
                else:
                    await update.message.reply_text(
                        text="هیچ کاربری برای ارسال پیام وجود ندارد.",
                        reply_markup=AdminKeyboard.main(),
                    )

            elif text == "❌ لغو":
                context.user_data.pop("broadcast_draft", None)
                await self.user.set_state(sender_id, "admin")
                await update.message.reply_text(
                    text="❌ ارسال پیام همگانی لغو شد.",
                    reply_markup=AdminKeyboard.main(),
                )

        # ══════════════════════════════════════════════════════════════════════
        #  Stats report
        # ══════════════════════════════════════════════════════════════════════

        elif text == "• گزارشات آماری •" and state == "admin":
            await update.message.reply_text("در حال دریافت گزارشات آماری...")

            try:
                reports_data = await self.api_request.get_admin_reports()

                if reports_data.get("error"):
                    await update.message.reply_text(
                        text=f"خطا در دریافت گزارشات: {reports_data.get('message', 'خطای نامشخص')}",
                        reply_markup=AdminKeyboard.main(),
                    )
                    return

                report_message = "📊 <b>گزارشات آماری سیستم</b>\n\n"

                if reports_data.get("monthly_analyses"):
                    report_message += "📈 <b>تعداد تحلیل‌های ماهانه:</b>\n"
                    for r in reports_data["monthly_analyses"]:
                        report_message += f"• {r['month']}: {r['total_analyses']} تحلیل\n"
                    report_message += "\n"

                if reports_data.get("weekly_analysis"):
                    wc = reports_data["weekly_analysis"]["total_analyses"]
                    report_message += f"📅 <b>تحلیل‌های هفته گذشته:</b> {wc} تحلیل\n\n"

                if reports_data.get("monthly_plan_subscriptions"):
                    report_message += "📦 <b>اشتراک‌های طرح ماهانه:</b>\n"
                    for mp in reports_data["monthly_plan_subscriptions"]:
                        report_message += (
                            f"• {mp['month']} - +{mp['package_days']} روز:"
                            f" {mp['total_subscriptions']} اشتراک\n"
                        )
                    report_message += "\n"

                if reports_data.get("plan_status"):
                    ps = reports_data["plan_status"]
                    report_message += (
                        "⏳ <b>وضعیت طرح‌ها:</b>\n"
                        f"• کاربران فعال: {ps['active_users']}\n"
                        f"• کاربران منقضی شده: {ps['expired_users']}\n"
                        f"• کاربران آزمایشی: {ps['trial_users']}\n\n"
                    )

                if reports_data.get("new_users"):
                    nu = reports_data["new_users"]
                    report_message += (
                        "👥 <b>کاربران جدید:</b>\n"
                        f"• ساعت گذشته: {nu['last_hour']} کاربر\n"
                        f"• روز گذشته: {nu['last_day']} کاربر\n\n"
                    )

                # Split if too long
                if len(report_message) > 4096:
                    chunks, current = [], ""
                    for line in report_message.split("\n"):
                        if len(current + line + "\n") > 4096:
                            chunks.append(current)
                            current = line + "\n"
                        else:
                            current += line + "\n"
                    if current:
                        chunks.append(current)

                    for idx, chunk in enumerate(chunks):
                        markup = AdminKeyboard.main() if idx == len(chunks) - 1 else None
                        await update.message.reply_text(
                            text=chunk,
                            parse_mode=ParseMode.HTML,
                            reply_markup=markup,
                        )
                else:
                    await update.message.reply_text(
                        text=report_message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=AdminKeyboard.main(),
                    )

            except Exception as e:
                logger.error(f"Error getting admin reports: {e}")
                await update.message.reply_text(
                    text="خطایی در دریافت گزارشات رخ داد. لطفا دوباره تلاش کنید.",
                    reply_markup=AdminKeyboard.main(),
                )
