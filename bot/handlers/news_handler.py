"""News analysis workflow handler."""

import re
import time
import asyncio
import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from crypto_symbols import resolve_symbol_contained, get_news_valid_symbols
from localization import text as tr
from keyboards import UserKeyboard
from constants import is_news_analysis_configured

logger = logging.getLogger(__name__)


class NewsHandler:
    """Handler for news analysis related interactions."""

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

    async def handle_news_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle initial news analysis button request."""
        if not is_news_analysis_configured():
            await update.message.reply_text(
                tr(language, "⚠️ News analysis is currently unavailable due to missing API key configuration (Brave/LLM key). Please contact support.", "⚠️ خدمات تحلیل اخبار به دلیل عدم تنظیم کلیدهای API (کلید جستجو/هوش مصنوعی) در حال حاضر غیرفعال است. لطفاً با پشتیبانی تماس بگیرید.")
            )
            return

        is_member, keyboard = await self.handler.check_required_channels(context, sender_id)
        if not is_member:
            msg = tr(language, "To use all bot features, please join the required channels first.", "برای بهره‌مندی کامل از خدمات ربات، لطفاً ابتدا در کانال‌های موردنیاز عضو شوید.")
            await update.message.reply_text(
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        await self.user.set_state(sender_id, "get_news")
        msg = tr(language, "Enter a *coin ticker* or *coin name*.\n📊 News analysis is available for the top 50 coins by market cap.\n📋 Examples: `BTC`, `ETH`, `Bitcoin`, or `Ethereum`\n🔄 News is refreshed every *24 hours*.\n\nNews analysis is free.", "لطفاً *نماد ارز* یا *نام ارز* مورد نظر را وارد کنید.\n📊 تحلیل اخبار برای پنجاه نماد بالای مارکت کپ در دسترس است.\n📋 برای مثال: `BTC` ، `ETH` یا `بیت‌کوین` ، `اتریوم`\n🔄اخبار هر *۲۴ ساعت* به‌روزرسانی می‌شود\n\nنمایش اخبار رایگان است .")
        await update.message.reply_text(text=msg, reply_markup=UserKeyboard.back(language), parse_mode=ParseMode.MARKDOWN)

    async def handle_symbol_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, text: str, language: str):
        """Handle symbol input when user is in get_news state."""
        if not is_news_analysis_configured():
            await update.message.reply_text(
                tr(language, "⚠️ News analysis is currently unavailable due to missing API key configuration (Brave/LLM key). Please contact support.", "⚠️ خدمات تحلیل اخبار به دلیل عدم تنظیم کلیدهای API (کلید جستجو/هوش مصنوعی) در حال حاضر غیرفعال است. لطفاً با پشتیبانی تماس بگیرید.")
            )
            await self.user.set_state(sender_id, "")
            return

        resolved = resolve_symbol_contained(text)
        if resolved:
            symbol = resolved
        elif re.match(r"^[A-Za-z0-9]+$", text.strip()):
            symbol = text.strip().upper()
        else:
            await update.message.reply_text(tr(language, "Please enter a valid ticker or English asset name, such as `BTC` or `Bitcoin`.", "لطفاً یک نماد معتبر وارد کنید. می‌توانید از نماد (مثل `BTC`) یا نام انگلیسی (مثل `Bitcoin`) یا نام فارسی (مثل `بیت‌کوین`) استفاده کنید."))
            return

        valid_symbols = get_news_valid_symbols()
        if symbol not in valid_symbols:
            await update.message.reply_text(tr(language, "Please enter a supported symbol. Available news symbols: ", "لطفا یک نماد معتبر وارد کنید. نمادهای معتبر برای تحلیل اخبار شامل: ") + ", ".join(valid_symbols))
            return

        if self.handler.is_pending(sender_id, "news"):
            await update.message.reply_text(
                tr(language, "Your previous request is still being processed.", "درخواست قبلی شما هنوز پاسخ داده نشده است.")
            )
            return

        self.handler.add_pending(sender_id, "news")

        try:
            me = await self.api_request.me(sender_id)

            if me and isinstance(me, dict):
                if "error" in me and me["error"]:
                    error_msg = tr(language, "Could not load your profile. Please try again.", f"خطا در دریافت پروفایل: {me.get('message', 'خطای نامشخص')}")
                    await update.message.reply_text(error_msg)
                    self.handler.remove_pending(sender_id, "news")
                    return
                elif "detail" in me:
                    error_msg = tr(language, "Could not load your profile. Please try again.", f"خطا در دریافت پروفایل: {me.get('detail', 'خطای نامشخص')}")
                    await update.message.reply_text(error_msg)
                    self.handler.remove_pending(sender_id, "news")
                    return

            if not me or not isinstance(me, dict):
                await update.message.reply_text(
                    tr(language, "❌ Your account could not be loaded. Send /start to register again, then retry.", "❌ اطلاعات حساب شما دریافت نشد. لطفاً /start را ارسال کنید و دوباره تلاش کنید.")
                )
                self.handler.remove_pending(sender_id, "news")
                return

            msg = tr(language, "🤖 Preparing news analysis\n⏳ This may take about 2–5 minutes.\n🕒 Please wait.", "🤖 در حال دریافت تحلیل اخبار \n⏳ این فرایند ممکن است حدود 2-5 دقیقه زمان ببرد.\n🕒 لطفاً منتظر بمانید.")

            progress_message = await update.message.reply_text(msg)

            task_key = f"news_{sender_id}_{symbol}_{int(time.time())}"

            task = asyncio.create_task(
                self.handler.process_news_in_background(
                    sender_id, symbol, "summary_sites",
                    progress_message, update, context, task_key
                )
            )

            self.handler.background_tasks[task_key] = task

        except Exception as e:
            print(f"Error setting up news analysis: {str(e)}")
            try:
                await update.message.reply_text(
                    tr(language, f"Could not start the news analysis: {str(e)}\nPlease send the symbol again in a moment.", f"خطا در راه‌اندازی تحلیل اخبار: {str(e)}\nلطفاً لحظاتی دیگر دوباره نماد را ارسال کنید.")
                )
            except Exception:
                pass
            self.handler.remove_pending(sender_id, "news")
