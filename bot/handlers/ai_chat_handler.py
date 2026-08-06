"""Financial AI chat handler."""

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from localization import text as tr
from keyboards import UserKeyboard
from constants import is_ai_chat_configured

logger = logging.getLogger(__name__)


class AIChatHandler:
    """Handler for financial AI chat interactions."""

    def __init__(self, main_handler):
        """Initialize with reference to parent PrivateHandler."""
        self.handler = main_handler

    @property
    def user(self):
        return self.handler.user

    @property
    def api_request(self):
        return self.handler.api_request

    @property
    def llm_chat(self):
        return self.handler.llm_chat

    async def handle_chat_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle AI chat button request."""
        if not is_ai_chat_configured():
            await update.message.reply_text(
                tr(language, "⚠️ AI chat service is currently unconfigured (missing API key). Please contact support.", "⚠️ سرویس چت با هوش مصنوعی در حال حاضر تنظیم نشده است (کلید API یافت نشد). لطفاً با پشتیبانی تماس بگیرید.")
            )
            return

        me = await self.api_request.me(sender_id)
        if not me or not isinstance(me, dict) or me.get("plan_status") != "active":
            await update.message.reply_text(
                tr(language, "⏳ AI chat is available only with an active plan. Please activate your subscription.", "⏳ استفاده از چت با هوش مصنوعی تنها برای کاربران با طرح فعال امکان‌پذیر است. لطفاً طرح خود را فعال کنید.")
            )
            return
        await self.user.set_state(sender_id, "ai_chat")

        msg = tr(language, "🤖 **Financial AI chat**\n\n✅ Chat mode is active!\n💬 Ask your financial questions here.\n📝 Tap Back to return.", "🤖 **چت با هوش مصنوعی مالی**\n\n✅ حالت چت فعال شد!\n💬 می‌تونی سوالات مالی‌تو بپرسی. پاسخ‌ها بر اساس کتاب‌های معتبر مالی داده می‌شن.\n📝 برای بازگشت، دکمه \"برگشت\" رو بزن.")

        await update.message.reply_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=UserKeyboard.ai_chat(language)
        )

    async def handle_clear_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle clear chat history request."""
        if not is_ai_chat_configured():
            await update.message.reply_text(
                tr(language, "⚠️ AI chat service is currently unconfigured (missing API key). Please contact support.", "⚠️ سرویس چت با هوش مصنوعی در حال حاضر تنظیم نشده است (کلید API یافت نشد). لطفاً با پشتیبانی تماس بگیرید.")
            )
            await self.user.set_state(sender_id, "")
            return

        me = await self.api_request.me(sender_id)
        if not me or not isinstance(me, dict) or me.get("plan_status") != "active":
            await update.message.reply_text(
                tr(language, "⏳ AI chat is available only with an active plan. Please activate your subscription.", "⏳ استفاده از چت با هوش مصنوعی تنها برای کاربران با طرح فعال امکان‌پذیر است. لطفاً طرح خود را فعال کنید.")
            )
            await self.user.set_state(sender_id, "")
            return
        success = await self.llm_chat.clear_conversation_history(str(sender_id))
        message = tr(language, "✅ Chat history cleared. A new conversation has started!", "✅ تاریخچه چت شما پاک شد. گفتگوی جدید شروع شد!") if success else tr(language, "⚠️ Could not clear history, but chat is still available.", "⚠️ خطا در پاک کردن تاریخچه، اما چت همچنان کار می‌کند.")
        await update.message.reply_text(message, reply_markup=UserKeyboard.ai_chat(language))

    async def handle_chat_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, text: str, language: str):
        """Handle text input in ai_chat state."""
        if not is_ai_chat_configured():
            await update.message.reply_text(
                tr(language, "⚠️ AI chat service is currently unconfigured (missing API key). Please contact support.", "⚠️ سرویس چت با هوش مصنوعی در حال حاضر تنظیم نشده است (کلید API یافت نشد). لطفاً با پشتیبانی تماس بگیرید.")
            )
            await self.user.set_state(sender_id, "")
            return

        me = await self.api_request.me(sender_id)
        if not me or not isinstance(me, dict) or me.get("plan_status") != "active":
            await update.message.reply_text(
                tr(language, "⏳ AI chat is available only with an active plan. Please activate your subscription.", "⏳ استفاده از چت با هوش مصنوعی تنها برای کاربران با طرح فعال امکان‌پذیر است. لطفاً طرح خود را فعال کنید.")
            )
            await self.user.set_state(sender_id, "")
            return

        if not text or len(text.strip()) == 0:
            await update.message.reply_text("لطفاً یک پیام معتبر وارد کنید.")
            return

        if len(text) > 2000:
            await update.message.reply_text("پیام شما خیلی طولانی است. لطفاً پیام کوتاه‌تری ارسال کنید.")
            return

        typing_message = await update.message.reply_text(tr(language, "Typing…", "درحال تایپ..."))

        try:
            response = await self.llm_chat.send_message(text.strip(), str(sender_id), language)

            if response.get("success", False):
                answer = response["answer"]

                if len(answer) > 4000:
                    chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                    await typing_message.edit_text(chunks[0])
                    for chunk in chunks[1:]:
                        await update.message.reply_text(chunk)
                else:
                    try:
                        await typing_message.edit_text(
                            answer,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception:
                        await typing_message.edit_text(answer)
            else:
                error_msg = response.get("error", "خطا در ارتباط با هوش مصنوعی.")
                logger.error(f"LLM chat returned error for user {sender_id}: {error_msg}")
                await typing_message.edit_text(f"❌ {error_msg}")

        except Exception as e:
            try:
                await typing_message.edit_text(
                    "❌ خطا در ارتباط با هوش مصنوعی. لطفاً دوباره تلاش کنید."
                )
            except Exception:
                await update.message.reply_text(
                    "❌ خطا در ارتباط با هوش مصنوعی. لطفاً دوباره تلاش کنید."
                )
            logger.error(f"LLM chat error for user {sender_id}: {str(e)}")
            print(f"LLM chat error for user {sender_id}: {str(e)}")
