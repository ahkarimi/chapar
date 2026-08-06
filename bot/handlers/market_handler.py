"""Gold and USD currency market handler."""

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from constants import (
    STATIC_MESSAGES_CHANNEL_ID,
    SM_GOLD_ID,
    SM_DOLLAR_ID,
    BOT_BRAND_HANDLE,
)
from localization import text as tr
from keyboards import UserKeyboard
from md2tgmd import escape

logger = logging.getLogger(__name__)


class MarketHandler:
    """Handler for live gold and currency price interactions."""

    def __init__(self, main_handler):
        """Initialize with reference to parent PrivateHandler."""
        self.handler = main_handler

    @property
    def user(self):
        return self.handler.user

    @property
    def api_request(self):
        return self.handler.api_request

    async def handle_market_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle market menu button request."""
        await self.user.set_state(sender_id, "analyze")
        await update.message.reply_text(
            tr(language, "💰📊 Live gold and USD prices", "💰📊 تحلیل طلا و دلار به همراه قیمت لحظه‌ای"),
            reply_markup=UserKeyboard.analyze(language)
        )

    async def handle_gold_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int):
        """Forward static gold analysis message."""
        await context.bot.forward_message(
            chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_GOLD_ID
        )

    async def handle_gold_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int):
        """Fetch and display live gold prices."""
        user_data = await self.user.get_user(sender_id)
        language = user_data.get("Language") if user_data else "fa"
        loading_message = await update.message.reply_text(tr(language, "Fetching gold prices...", "در حال دریافت قیمت‌های طلا"))

        try:
            currency_data = await self.api_request.get_currency(sender_id)

            if isinstance(currency_data, dict) and currency_data.get("error"):
                await loading_message.edit_text(f"{tr(language, 'Error fetching prices:', 'خطا در دریافت قیمت‌ها:')} {currency_data.get('message', tr(language, 'Unknown error', 'خطای نامشخص'))}")
                return

            if isinstance(currency_data, dict) and "detail" in currency_data:
                await loading_message.edit_text(f"{tr(language, 'Error:', 'خطا:')} {currency_data['detail']}")
                return

            gold_slugs = ['ONS', 'TALA_24', 'TALA_18', 'SEKE_BAHAR', 'SEKE_EMAMI']
            gold_items = []

            if "data" in currency_data and isinstance(currency_data["data"], list):
                for item in currency_data["data"]:
                    if item.get("slug") in gold_slugs:
                        gold_items.append(item)

            if not gold_items:
                await loading_message.edit_text(tr(language, "Gold prices are currently unavailable.", "قیمت‌های طلا در حال حاضر در دسترس نیستند."))
                return

            msg = escape(tr(language, "🏆 Live Gold & Coin Prices 🏆\n\n", "🏆 قیمت‌های لحظه‌ای طلا و سکه 🏆\n\n"))

            for item in gold_items:
                name = escape(item.get("name", ""))
                price = item.get("price", "")
                change = item.get("change", "")
                change_percent = item.get("change_percent", "")
                last_update = escape(item.get("jalali_last_update", ""))

                try:
                    if price and isinstance(price, (str, int, float)):
                        price_str = str(price).replace(",", "")
                        if "." in price_str:
                            int_part, dec_part = price_str.split(".")
                            price = "{:,}".format(int(int_part)) + "." + dec_part
                        else:
                            price = "{:,}".format(int(price_str))
                except (ValueError, TypeError):
                    pass

                price = escape(str(price))

                change_emoji = "⚪️"
                change_direction_emoji = "📊"
                try:
                    if change and change_percent:
                        change_value = float(str(change).replace(",", ""))
                        if change_value > 0:
                            change_emoji = "🟢"
                            change_direction_emoji = "📈"
                        elif change_value < 0:
                            change_emoji = "🔴"
                            change_direction_emoji = "📉"
                except (ValueError, TypeError):
                    pass

                lbl_price = escape(tr(language, "💰 Price:", "💰 قیمت:"))
                msg += f"{change_emoji} **{name}**\n"
                msg += f"{lbl_price} **{price}**\n"

                if change and change_percent:
                    try:
                        change_str = str(change).replace(",", "")
                        if "." in change_str:
                            int_part, dec_part = change_str.split(".")
                            formatted_change = "{:,}".format(int(int_part)) + "." + dec_part
                        else:
                            formatted_change = "{:,}".format(int(change_str))
                    except (ValueError, TypeError):
                        formatted_change = change

                    formatted_change = escape(str(formatted_change))
                    change_percent = escape(str(change_percent))
                    lbl_change = escape(tr(language, "Change:", "تغییر:"))
                    msg += f"{change_direction_emoji} {lbl_change} **{formatted_change}** \\(**{change_percent}%**\\)\n"

                if last_update:
                    lbl_update = escape(tr(language, "🕒 Last update:", "🕒 آخرین به‌روزرسانی:"))
                    msg += f"{lbl_update} **{last_update}**\n"

                msg += "\n"

            msg += escape(tr(language, "⚠️ Prices update every 10 minutes", "⚠️ قیمت‌ها هر ۱۰ دقیقه به‌روز رسانی می‌شوند"))
            tagline = tr(language, "Data-driven analysis, not guessing:", "تحلیل مبتنی بر داده، نه حدس:")
            msg += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"

            await loading_message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )

        except Exception as e:
            print(f"Error fetching gold prices: {str(e)}")
            await loading_message.edit_text(tr(language, "Error fetching gold prices. Please try again.", "خطا در دریافت قیمت‌های طلا. لطفا مجددا تلاش کنید."))

    async def handle_dollar_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int):
        """Forward static dollar analysis message."""
        await context.bot.forward_message(
            chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_DOLLAR_ID
        )

    async def handle_usd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int):
        """Fetch and display live USD/currency prices."""
        user_data = await self.user.get_user(sender_id)
        language = user_data.get("Language") if user_data else "fa"
        loading_message = await update.message.reply_text(tr(language, "Fetching currency prices...", "در حال دریافت قیمت‌های ارز"))

        try:
            currency_data = await self.api_request.get_currency(sender_id)

            if isinstance(currency_data, dict) and currency_data.get("error"):
                await loading_message.edit_text(f"{tr(language, 'Error fetching prices:', 'خطا در دریافت قیمت‌ها:')} {currency_data.get('message', tr(language, 'Unknown error', 'خطای نامشخص'))}")
                return

            if isinstance(currency_data, dict) and "detail" in currency_data:
                await loading_message.edit_text(f"{tr(language, 'Error:', 'خطا:')} {currency_data['detail']}")
                return

            currency_slugs = ['TETHER', 'USD', 'EUR']
            currency_items = []

            if "data" in currency_data and isinstance(currency_data["data"], list):
                for item in currency_data["data"]:
                    if item.get("slug") in currency_slugs:
                        currency_items.append(item)

            if not currency_items:
                await loading_message.edit_text(tr(language, "Currency prices are currently unavailable.", "قیمت‌های ارز در حال حاضر در دسترس نیستند."))
                return

            msg = escape(tr(language, "💵 Live Currency Prices 💵\n\n", "💵 قیمت‌های لحظه‌ای ارز 💵\n\n"))

            for item in currency_items:
                name = escape(item.get("name", ""))
                price = item.get("price", "")
                change = item.get("change", "")
                change_percent = item.get("change_percent", "")
                last_update = escape(item.get("jalali_last_update", ""))

                try:
                    if price and isinstance(price, (str, int, float)):
                        price_str = str(price).replace(",", "")
                        if "." in price_str:
                            int_part, dec_part = price_str.split(".")
                            price = "{:,}".format(int(int_part)) + "." + dec_part
                        else:
                            price = "{:,}".format(int(price_str))
                except (ValueError, TypeError):
                    pass

                price = escape(str(price))

                change_emoji = "⚪️"
                change_direction_emoji = "📊"
                try:
                    if change and change_percent:
                        change_value = float(str(change).replace(",", ""))
                        if change_value > 0:
                            change_emoji = "🟢"
                            change_direction_emoji = "📈"
                        elif change_value < 0:
                            change_emoji = "🔴"
                            change_direction_emoji = "📉"
                except (ValueError, TypeError):
                    pass

                lbl_price = escape(tr(language, "💰 Price:", "💰 قیمت:"))
                msg += f"{change_emoji} **{name}**\n"
                msg += f"{lbl_price} **{price}**\n"

                if change and change_percent:
                    try:
                        change_str = str(change).replace(",", "")
                        if "." in change_str:
                            int_part, dec_part = change_str.split(".")
                            formatted_change = "{:,}".format(int(int_part)) + "." + dec_part
                        else:
                            formatted_change = "{:,}".format(int(change_str))
                    except (ValueError, TypeError):
                        formatted_change = change

                    formatted_change = escape(str(formatted_change))
                    change_percent = escape(str(change_percent))
                    lbl_change = escape(tr(language, "Change:", "تغییر:"))
                    msg += f"{change_direction_emoji} {lbl_change} **{formatted_change}** \\(**{change_percent}%**\\)\n"

                if last_update:
                    lbl_update = escape(tr(language, "🕒 Last update:", "🕒 آخرین به‌روزرسانی:"))
                    msg += f"{lbl_update} **{last_update}**\n"

                msg += "\n"

            msg += escape(tr(language, "⚠️ Prices update every 10 minutes", "⚠️ قیمت‌ها هر ۱۰ دقیقه به‌روز رسانی می‌شوند"))
            tagline = tr(language, "Data-driven analysis, not guessing:", "تحلیل مبتنی بر داده، نه حدس:")
            msg += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"

            await loading_message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )

        except Exception as e:
            print(f"Error fetching currency prices: {str(e)}")
            await loading_message.edit_text(tr(language, "Error fetching currency prices. Please try again.", "خطا در دریافت قیمت‌های ارز. لطفا مجددا تلاش کنید."))
