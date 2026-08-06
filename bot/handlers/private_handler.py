import re
import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram import error as tg_error
from tools import LLMChatService
from keyboards import UserKeyboard
from localization import is_button, text as tr
from md2tgmd import escape

from constants import (
    STATIC_MESSAGES_CHANNEL_ID,
    SM_GUIDE_ID,
)

from .message_utils import MessageUtilsMixin
from .news_workflow import NewsWorkflowMixin
from .chart_handler import ChartHandler
from .news_handler import NewsHandler
from .ai_chat_handler import AIChatHandler
from .market_handler import MarketHandler
from .profile_handler import ProfileHandler

logger = logging.getLogger(__name__)


class PrivateHandler(MessageUtilsMixin, NewsWorkflowMixin):
    """Handler for private chat messages delegating to domain sub-handlers."""

    def __init__(self, user_db, settings_db, api_request):
        """Initialize with database, API clients, and domain sub-handlers."""
        self.user = user_db
        self.settings = settings_db
        self.api_request = api_request
        self.pending_requests = {}
        self.pending_locks = {}
        self.verify_locks = {}
        self.start_time = None
        self.bot_username = None
        # Tasks store to maintain references to background tasks
        self.background_tasks = {}
        # Cache for force joins to avoid repeated database calls
        self._force_joins_cache = None
        self._force_joins_cache_time = 0
        # Initialize LLM chat service
        self.llm_chat = LLMChatService()

        # Initialize domain-specific sub-handlers
        self.chart_handler = ChartHandler(self)
        self.news_handler = NewsHandler(self)
        self.ai_chat_handler = AIChatHandler(self)
        self.market_handler = MarketHandler(self)
        self.profile_handler = ProfileHandler(self)

    def set_bot_info(self, username, start_time):
        """Set bot username and start time."""
        self.bot_username = username
        self.start_time = start_time

    # Forwarding methods for chart background tasks to maintain API compatibility
    async def process_analysis_in_background(self, *args, **kwargs):
        """Delegate background chart analysis to ChartHandler."""
        return await self.chart_handler.process_analysis_in_background(*args, **kwargs)

    async def handle_analysis_result(self, *args, **kwargs):
        """Delegate chart analysis result handling to ChartHandler."""
        return await self.chart_handler.handle_analysis_result(*args, **kwargs)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming private messages by routing to sub-handlers."""
        if self.start_time and update.message.date.timestamp() < self.start_time:
            return

        text = update.message.text
        sender_id = update.effective_user.id

        user = await self.user.get_user(sender_id)
        state = user["State"]
        language = user.get("Language")

        # Language selection flow
        if text in {"English 🇬🇧", "فارسی 🇮🇷"}:
            language = "en" if text.startswith("English") else "fa"
            await self.user.set_language(sender_id, language)
            state = ""
            text = "/start"
        elif is_button(text, "language") or not language:
            await self.user.set_state(sender_id, "language_selection")
            await update.message.reply_text(
                "Please choose your language.\nلطفاً زبان خود را انتخاب کنید.",
                reply_markup=UserKeyboard.language_selection(),
            )
            return

        # Handle /start command
        if text.startswith("/start"):
            is_member, keyboard = await self.check_required_channels(context, sender_id)
            if not is_member:
                msg = tr(language, "To use all bot features, please join the required channels first.", "برای بهره‌مندی کامل از خدمات ربات، لطفاً ابتدا در کانال‌های موردنیاز عضو شوید.")
                await update.message.reply_text(
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

            reg_success = await self.register_logic(update, context, sender_id)
            if reg_success:
                welcome = tr(
                    language,
                    "✅ Welcome to Chapar\n\nI monitor markets, build charts, and provide AI-powered analysis.\nAnalysis—not trading signals.\n\nTap Chart analysis to begin 👇",
                    "✅ به چاپار خوش اومدی\n\nمن بازار رو رصد می‌کنم، چارت می‌کشم\nو تحلیل هوش مصنوعی بهت میدم.\nنه سیگنال، بلکه تحلیل.\n\nدکمه تحلیل چارت رو بزن که شروع کنیم 👇",
                )
                await update.message.reply_text(
                    text=welcome,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
                )
            else:
                await update.message.reply_text(tr(language, "❌ Registration failed.", "❌ خطا در ثبت نام."))
            return

        # Handle /help command
        elif text == "/help":
            await self.show_help_message(update, context, sender_id)
            return

        # Handle back button
        elif is_button(text, "back") and state != "" and state != "waiting_for_analysis":
            expected_back_states = ["get_analysis", "verify", "analyze", "education_prize", "get_news", "credit_menu", "ai_chat"]
            if state not in expected_back_states:
                print(f"INFO: Back button pressed in unexpected state '{state}' for user {sender_id}. Resetting to main menu.")

            await self.user.set_state(sender_id, "")
            await update.message.reply_text(
                text=tr(language, "Back to the main menu", "برگشت به منوی اصلی"),
                reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
            )

        # Profile button
        elif is_button(text, "profile") and state == "":
            await self.profile_handler.handle_profile_request(update, context, sender_id, language)

        # Education button from main menu
        elif (is_button(text, "education") and state == "") or text == '• راهنما •':
            await context.bot.forward_message(
                chat_id=sender_id, from_chat_id=STATIC_MESSAGES_CHANNEL_ID, message_id=SM_GUIDE_ID
            )

        # Chart analysis request
        elif (
            is_button(text, "chart") or
            text == "تحلیل چارت" or
            text == "/start get_analysis"
        ) and state == "":
            await self.chart_handler.handle_chart_request(update, context, sender_id, language)

        # Ticker input for chart analysis
        elif state == "get_analysis":
            await self.chart_handler.handle_symbol_input(update, context, sender_id, text, language)

        # Back button while waiting for chart analysis
        elif is_button(text, "back") and state == "waiting_for_analysis":
            await self.user.set_state(sender_id, "")
            await update.message.reply_text(
                tr(
                    language,
                    "You returned to the main menu. Your chart analysis is still running in the background, and I will send it when it is ready.",
                    "شما به منوی اصلی بازگشتید. تحلیل در پس‌زمینه ادامه دارد و نتیجه آن پس از آماده شدن برای شما ارسال خواهد شد.",
                ),
                reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language)
            )

        # Free credit button in education_prize state
        elif text == "• دریافت اعتبار رایگان •" and state == "education_prize":
            await self.profile_handler.handle_free_credit_request(update, context, sender_id, language)

        # AI chat button
        elif is_button(text, "chat") and state == "":
            await self.ai_chat_handler.handle_chat_request(update, context, sender_id, language)

        # Clear chat history button
        elif is_button(text, "clear_chat") and state == "ai_chat":
            await self.ai_chat_handler.handle_clear_chat(update, context, sender_id, language)

        # AI chat text message
        elif state == "ai_chat" and not is_button(text, "back") and not is_button(text, "clear_chat"):
            await self.ai_chat_handler.handle_chat_message(update, context, sender_id, text, language)

        # UID verification input
        elif state == "verify":
            await self.profile_handler.handle_uid_input(update, context, sender_id, text, language)

        # Subscription button
        elif is_button(text, "subscription") and state == "":
            await self.profile_handler.handle_subscription_request(update, context, sender_id, language)

        # News analysis button
        elif is_button(text, "news") and state == "":
            await self.news_handler.handle_news_request(update, context, sender_id, language)

        # Ticker input for news analysis
        elif state == "get_news":
            await self.news_handler.handle_symbol_input(update, context, sender_id, text, language)

        # Prize button in education_prize state
        elif is_button(text, "prize") and state == "education_prize":
            await self.profile_handler.handle_prize_request(update, context, sender_id, language)

        # Education button in education_prize state
        elif is_button(text, "education") and state == "education_prize":
            await self.profile_handler.handle_education_request(update, context, sender_id, language)

        # Market button
        elif is_button(text, "market") and state == "":
            await self.market_handler.handle_market_request(update, context, sender_id, language)

        # Gold static analysis
        elif text == "• تحلیل طلا •" and state == "analyze":
            await self.market_handler.handle_gold_analysis(update, context, sender_id)

        # Gold live price
        elif is_button(text, "gold_price") and state == "analyze":
            await self.market_handler.handle_gold_price(update, context, sender_id)

        # Dollar static analysis
        elif text == "• تحلیل دلار •" and state == "analyze":
            await self.market_handler.handle_dollar_analysis(update, context, sender_id)

        # USD live price
        elif is_button(text, "usd_price") and state == "analyze":
            await self.market_handler.handle_usd_price(update, context, sender_id)

        # Unsupported input at main menu
        elif state == "" and not any(is_button(text, key) for key in (
            "chart", "chat", "news", "subscription", "market", "profile", "admin", "language"
        )):
            await self.show_help_message(update, context, sender_id)

    async def show_help_message(self, update, context, sender_id):
        """Show help message to user."""
        language = (await self.user.get_user(sender_id)).get("Language") or "fa"
        help_text = tr(language, "🤖 *Bot help*\n\n/start - Restart the bot\n🔵 You can also use the menu buttons:\n📊 Chart analysis\n💬 Chat with AI\n📰 News analysis (free)\n💰 Gold & USD\n👤 My profile\n🌐 Language\n", "🤖*راهنمای دستورات ربات*\n\n/start - شروع مجدد ربات\n🔵 همچنین می‌توانید از دکمه‌های داخل ربات استفاده کنید:\n📊 تحلیل چارت\n💬 چت با AI\n📰 تحلیل اخبار (رایگان)\n💰 طلا و دلار\n👤 پروفایل من\n🌐 زبان\n")

        help_video = self.settings.get_help_video()
        if help_video:
            try:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=help_video,
                    caption="🎬 لطفا  این ویدیو راهنما را برای استفاده از ربات ببینید.",
                )
            except Exception as e:
                print(f"Error sending help video: {e}")

        await update.message.reply_text(
            text=help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=UserKeyboard.main(self.settings.is_admin(sender_id), language),
        )

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        user_id = update.effective_user.id
        callback_data = query.data

        user = await self.user.get_user(user_id)
        language = user.get("Language") or "fa"

        if not callback_data.startswith("section_"):
            await query.answer()

        if callback_data.startswith("section_"):
            await self.chart_handler.handle_section_callback(update, query, user_id, callback_data)
            return

        elif callback_data == "check_membership":
            await self.invalidate_membership_cache(user_id)
            is_member, keyboard = await self.check_required_channels(context, user_id)
            if not is_member:
                msg = "برای بهره‌مندی کامل از خدمات ربات، لطفاً ابتدا در کانال‌های موردنیاز عضو شوید."
                try:
                    await query.message.edit_text(
                        text=msg,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except tg_error.BadRequest as e:
                    if "message is not modified" not in str(e).lower():
                        print(f"Error editing message: {e}")
                        await query.answer("خطایی رخ داد، لطفا دوباره تلاش کنید", show_alert=True)
                return
            else:
                await query.edit_message_text(text="عضویت شما تایید شد! در حال راه اندازی.")
                reg_success = await self.register_logic(update, context, user_id)
                if reg_success:
                    await context.bot.send_message(chat_id=user_id,
                                                   text="✅ .به ربات تحلیل ارز دیجیتال خوش آمدید! برای شروع، *تحلیل چارت* را بزنید",
                                                   reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language),
                                                   parse_mode=ParseMode.MARKDOWN)
                else:
                    print(f"Error in registration {user_id}")
                return

        elif callback_data.startswith("analyze_"):
            await self.chart_handler.handle_analyze_callback(update, query, user_id, callback_data, context)
            return

        elif callback_data == "back_main":
            await self.user.set_state(user_id, "")
            await query.message.edit_text(
                "برگشت به منوی اصلی",
                reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language)
            )

        elif callback_data == "show_subscription":
            await self.profile_handler.handle_subscription_request(update, context, user_id, language)

    async def register_logic(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
        """Attempts to register the user by calling the API."""
        try:
            tg_user = update.effective_user
            full_name = " ".join(
                part for part in [tg_user.first_name, tg_user.last_name] if part
            ).strip() or None
            tg_username = tg_user.username or None

            result = await self.api_request.add_user(
                user_id, name=full_name, telegram_username=tg_username
            )
            if not isinstance(result, dict) or result.get("error") or result.get("detail"):
                logger.error("Registration failed for user %s: %s", user_id, result)
                return False
            await self.user.set_state(user_id, "")
            return True
        except Exception as e:
            print(f"Unexpected error in register_logic: {e}")
            return False
