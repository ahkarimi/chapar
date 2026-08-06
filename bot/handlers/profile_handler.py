"""User profile, subscription, and UID verification handler."""

import re
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from constants import (
    STATIC_MESSAGES_CHANNEL_ID,
    SM_GUIDE_ID,
    SM_INCREASE_CREDIT_ID,
    SM_PRIZE_ID,
    is_toobit_verification_configured,
)
from localization import text as tr, button
from keyboards import UserKeyboard
from md2tgmd import escape

logger = logging.getLogger(__name__)


class ProfileHandler:
    """Handler for profile, UID verification, subscription, and educational content."""

    def __init__(self, main_handler):
        """Initialize with reference to parent PrivateHandler."""
        self.handler = main_handler

    @property
    def user(self):
        return self.handler.user

    @property
    def settings(self):
        return self.handler.settings

    @property
    def api_request(self):
        return self.handler.api_request

    async def handle_profile_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle profile button request."""
        loading_message = await update.message.reply_text(tr(language, "Loading your profile…", "در حال دریافت اطلاعات پروفایل"))

        try:
            me = await self.api_request.me(sender_id)

            if me and isinstance(me, dict):
                if "error" in me and me["error"]:
                    last_error = me.get('message', 'خطای نامشخص')
                    error_status = me.get('status')

                    if error_status == 404:
                        error_msg = "پروفایل شما در سرور اصلی یافت نشد. در حال ثبت نام مجدد"
                        await loading_message.edit_text(error_msg)

                        reg_success = await self.handler.register_logic(update, context, sender_id)
                        if reg_success:
                            await loading_message.edit_text(
                                error_msg + "\n✅ ثبت نام انجام شد. لطفا دوباره دکمه پروفایل را بزنید."
                            )
                        else:
                            await loading_message.edit_text(error_msg + "\n❌ خطا در سرور.")
                        return

                    await loading_message.edit_text(last_error)
                    return
                elif "detail" in me:
                    await loading_message.edit_text(me["detail"])
                    return

            await loading_message.delete()

            if not me or not isinstance(me, dict):
                await update.message.reply_text("پروفایل شما یافت نشد. لطفا با پشتیبانی تماس بگیرید.")
                return

            plan_info_map = {
                'trial': ('⏳', tr(language, 'Free trial', 'پلن آزمایشی رایگان')),
                'active': ('💎', tr(language, 'Unlimited plan', 'پلن بی نهایت')),
                'expired': ('❌', tr(language, 'Expired plan', 'پلن منقضی شده')),
            }
            plan_status = me.get('plan_status', 'unknown')
            if plan_status in plan_info_map:
                plan_emoji, plan_label = plan_info_map[plan_status]
            else:
                plan_emoji, plan_label = ('❓', escape(str(plan_status)))

            remaining_time_human = me.get('remaining_time_human', '۰ روز')
            plan_end_date_human = me.get('plan_end_date_human', 'نامشخص')
            if language == "en":
                remaining_time_human = f"{me.get('remaining_days', 0)} days"
                plan_end_date_human = str(me.get('plan_end_date') or "Unknown")[:10]

            sep = escape('━━━━━━━━━━━━━━━')
            user_id_str = escape(str(me.get('id', 'نامشخص')))
            total_requests = escape(str(me.get('total_requests', 0)))
            name_val = escape(me['name']) if me.get('name') else None
            phone_val = escape(me['phone_number']) if me.get('phone_number') else None
            tg_username_val = escape(me['telegram_username']) if me.get('telegram_username') else None
            remaining_val = escape(remaining_time_human) if remaining_time_human else escape('نامشخص')
            end_date_val = escape(plan_end_date_human) if plan_end_date_human else escape('نامشخص')

            msg = f"🌟 *{tr(language, 'Your profile', 'پروفایل شما')}* 🌟\n{sep}\n\n"
            msg += f"👤 *{tr(language, 'Account details:', 'اطلاعات حساب:')}*\n"
            msg += f"🆔 {tr(language, 'ID', 'آیدی')}: `{user_id_str}`\n"

            if name_val:
                msg += f"👤 {tr(language, 'Name', 'نام')}: `{name_val}`\n"

            if phone_val:
                msg += f"📞 {tr(language, 'Phone', 'شماره تلفن')}: `{phone_val}`\n"

            if tg_username_val:
                msg += f"🆔 {tr(language, 'Telegram username', 'یوزرنیم تلگرام')}: @{tg_username_val}\n"

            msg += f"📊 {tr(language, 'Analyses', 'تعداد تحلیل‌ها')}: *{total_requests}*\n"

            msg += f"\n{sep}\n"
            msg += f"💼 *{tr(language, 'Subscription status:', 'وضعیت اشتراک:')}*\n\n"
            msg += f"{plan_emoji} *{plan_label}*\n"

            if plan_end_date_human and plan_end_date_human != 'نامشخص':
                msg += f"📅 {tr(language, 'End date', 'تاریخ پایان')}: {end_date_val}\n"

            msg += f"⏱ {tr(language, 'Time remaining', 'زمان باقی‌مانده')}: *{remaining_val}*\n"

            msg += f"\n{sep}\n"
            if plan_status == 'expired':
                msg += "💡 برای فعال‌سازی مجدد، از دکمه «⭐️ اشتراک ماهانه» استفاده کنید\\."
            elif plan_status == 'trial':
                msg += "💡 برای ارتقا به پلن ویژه، از دکمه «⭐️ اشتراک ماهانه» استفاده کنید\\."
            else:
                msg += "✨ از همراهی شما با چاپار سپاسگزاریم\\!"

            inline_keyboard = [
                [InlineKeyboardButton(button("subscription", language), callback_data="show_subscription")]
            ]

            await update.message.reply_text(
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(inline_keyboard)
            )
        except Exception as e:
            print(f"Error displaying profile: {str(e)}")
            await update.message.reply_text("خطایی در نمایش پروفایل رخ داد. لطفا مجددا تلاش کنید.")

    async def handle_free_credit_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle free credit button request in education_prize state."""
        invitation_link = self.settings.get_toobit_invitation_link()

        if not invitation_link:
            await update.message.reply_text(
                tr(language, "⚠️ UID verification is currently unavailable due to missing exchange configuration.", "⚠️ لینک دعوت توبیت یافت نشد. لطفا با ادمین تماس بگیرید.")
            )
            return

        msg = f'''برای دریافت اعتبار رایگان، کافیست چند گام ساده را دنبال کنید:

1.<b> ثبت نام در صرافی توبیت </b>: از طریق لینک زیر، در صرافی توبیت ثبت‌نام کنید. 🔗
{invitation_link}


2. <b> وارد کردن کد UID</b>: کد UID حساب کاربری توبیت خود را در این بخش وارد کنید. 🔑

3. <b>دریافت خودکار ۱۰ اعتبار رایگان</b>: به محض وارد کردن کد، اعتبار رایگان به ربات شما به صورت خودکار اضافه می‌شود. 🎉

فرآیند ساده است و تنها چند دقیقه زمان می‌برد ⏳. با ثبت‌نام و دریافت این اعتبار، از مزایای ویژه آن بهره‌مند شوید! 🚀'''

        await self.user.set_state(sender_id, "verify")
        await update.message.reply_text(text=msg, parse_mode=ParseMode.HTML, reply_markup=UserKeyboard.back(language))

    async def handle_uid_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, text: str, language: str):
        """Handle UID text input in verify state."""
        if not re.match(r"^[0-9]+$", text):
            await update.message.reply_text("لطفا UID را تنها به صورت یک عدد انگلیسی وارد کنید.")
            return

        invitation_link = self.settings.get_toobit_invitation_link()
        if not invitation_link:
            await update.message.reply_text(
                tr(language, "⚠️ UID verification is currently unavailable due to missing exchange configuration.", "⚠️ لینک دعوت توبیت یافت نشد. لطفا با ادمین تماس بگیرید.")
            )
            await self.user.set_state(sender_id, "")
            return

        progress_message = await update.message.reply_text("در حال بررسی UID")

        if sender_id not in self.handler.verify_locks:
            self.handler.verify_locks[sender_id] = asyncio.Lock()

        async with self.handler.verify_locks[sender_id]:
            if await self.user.toobit_uid_exists(text):
                await progress_message.edit_text("این UID قبلا تایید شده است.")
                return

            try:
                result = await self.api_request.verify(sender_id, text)

                if result and result.get("status") == "success":
                    verification_success = True
                    invitation_code = result.get("data", {}).get("invitation_code", "")
                else:
                    verification_success = False
                    error_msg = result.get('message', 'خطای نامشخص') if result else 'خطای در ارتباط با سرور'

                    if result and result.get('status') == 404:
                        error_msg = "UID یا کد دعوت نامعتبر است."
                    elif result and result.get('status') in [401, 403]:
                        error_msg = "دسترسی به API محدود شده است. لطفا با پشتیبانی تماس بگیرید."
                    elif result and result.get('status') and isinstance(result.get('status'), int) and result.get('status') >= 500:
                        error_msg = "سرویس صحت‌سنجی صرافی به دلیل عدم پیکربندی سرور در دسترس نیست. لطفاً با پشتیبانی تماس بگیرید."

            except Exception as e:
                verification_success = False
                error_msg = f"خطا در صحت سنجی: {str(e)}"

            if not verification_success:
                error_message = error_msg if 'error_msg' in locals() else "صحت‌سنجی انجام نشد. لطفاً بررسی کنید که با یکی از لینک‌های دعوت معتبر ثبت‌نام کرده باشید."
                await progress_message.edit_text(error_message)
                return

            await self.user.set_toobit_uid(sender_id, text)
            await self.user.set_state(sender_id, "")

            try:
                await progress_message.delete()
            except Exception as del_error:
                print(f"Error deleting progress message: {str(del_error)}")
                try:
                    await progress_message.edit_text("ثبت نام شما با موفقیت انجام شد.")
                except Exception:
                    pass

            success_msg = "✅ ثبت نام شما با موفقیت انجام شد. ۷ روز به طرح شما اضافه شد."
            if 'invitation_code' in locals() and invitation_code:
                success_msg += f"\n🎯 کد دعوت شما: {invitation_code}"

            await update.message.reply_text(
                success_msg,
                reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
            )

    async def handle_subscription_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle subscription button request."""
        await context.bot.forward_message(
            chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_INCREASE_CREDIT_ID
        )
        await self.user.set_state(sender_id, "")
        await update.message.reply_text(
            "برگشت به منوی اصلی",
            reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
        )

    async def handle_prize_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle prize button request in education_prize state."""
        await context.bot.forward_message(
            chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_PRIZE_ID
        )
        await self.user.set_state(sender_id, "")
        await update.message.reply_text(
            "برگشت به منوی اصلی",
            reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
        )

    async def handle_education_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle education button request."""
        await context.bot.forward_message(
            chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_GUIDE_ID
        )
        if await self.user.get_user_state(sender_id) if hasattr(self.user, 'get_user_state') else False:
            pass
        await self.user.set_state(sender_id, "")
        await update.message.reply_text(
            "برگشت به منوی اصلی",
            reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
        )
