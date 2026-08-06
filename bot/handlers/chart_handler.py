"""Chart analysis workflow and background task handler."""

import re
import base64
import asyncio
import logging
import random
import time
from io import BytesIO

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from constants import BOT_BRAND_HANDLE, BOT_RESULTS_CHANNEL, is_chart_analysis_configured
from database.cache import CacheManager
from crypto_symbols import resolve_symbol_contained
from services.trending_service import get_trending_coins
from localization import text as tr, button
from keyboards import UserKeyboard
from md2tgmd import escape

logger = logging.getLogger(__name__)


class ChartHandler:
    """Handler for chart analysis related interactions."""

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

    async def handle_chart_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, language: str):
        """Handle initial chart analysis button request."""
        if not is_chart_analysis_configured():
            await update.message.reply_text(
                tr(language, "⚠️ Chart analysis is currently unavailable due to missing API key configuration. Please contact support.", "⚠️ خدمات تحلیل چارت به دلیل عدم تنظیم کلید API در حال حاضر غیرفعال است. لطفاً با پشتیبانی تماس بگیرید.")
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

        me = await self.api_request.me(sender_id)
        if not me or not isinstance(me, dict) or me.get("error"):
            await update.message.reply_text(
                tr(language, "❌ Your account could not be loaded. Send /start to register again, then retry.", "❌ اطلاعات حساب شما دریافت نشد. لطفاً /start را ارسال کنید و دوباره تلاش کنید.")
            )
            return
        if me.get("plan_status") == "expired":
            await update.message.reply_text(
                tr(language, "⏳ Your plan has expired. Renew it to receive chart analysis.\n✅ News analysis and prices remain free.", "⏳ طرح شما منقضی شده است. برای دریافت تحلیل، لطفاً طرح خود را تمدید کنید.\n✅ تحلیل اخبار و قیمت‌ها همچنان رایگان هستند."),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await self.user.set_state(sender_id, "get_analysis")

        msg = tr(language, "🔍 Which symbol should I analyze?\n\nType a name or ticker, for example `BTC` or `Bitcoin`.\n\n", "🔍 کدوم نماد رو بررسی کنم؟\n\nاسم یا نماد بنویس:\nمثلاً `BTC` یا `بیت‌کوین`\n\n")
        msg += "━━━━━━━━━━━━━━━\n"

        trending = await get_trending_coins()
        if trending:
            selected = random.sample(trending, min(4, len(trending)))
            msg += tr(language, "📡 Trending now:\n\n", "📡 الان روی این‌ها زوم کردم:\n\n")
            for i, c in enumerate(selected):
                msg += f"{i+1}. `{c['symbol']}`\n"
            msg += tr(language, "_These symbols have interesting chart structures. Pick one 👇_", "_این نمادها ساختار چارتی جالبی دارن، نمادش رو بگو 👇_")

        await update.message.reply_text(text=msg, reply_markup=UserKeyboard.back(language), parse_mode=ParseMode.MARKDOWN)

    async def handle_symbol_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, sender_id: int, text: str, language: str):
        """Handle symbol input when user is in get_analysis state."""
        if not is_chart_analysis_configured():
            await update.message.reply_text(
                tr(language, "⚠️ Chart analysis is currently unavailable due to missing API key configuration. Please contact support.", "⚠️ خدمات تحلیل چارت به دلیل عدم تنظیم کلید API در حال حاضر غیرفعال است. لطفاً با پشتیبانی تماس بگیرید.")
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

        if not resolved:
            await update.message.reply_text(tr(language, "This symbol is not listed on Toobit's spot market. Please try another symbol.", "این نماد در نمادهای اسپات صرافی توبیت لیست نشده. لطفاً نماد دیگری ارسال کنید."))
            return

        if symbol != "USDT" and not symbol.endswith("USDT"):
            symbol += "USDT"

        if self.handler.is_pending(sender_id, "analysis"):
            await update.message.reply_text(
                tr(language, "Your previous request is still being processed.", "درخواست قبلی شما هنوز پاسخ داده نشده است.")
            )
            return

        self.handler.add_pending(sender_id, "analysis")

        try:
            me = await self.api_request.me(sender_id)

            if me and isinstance(me, dict):
                if "error" in me and me["error"]:
                    error_msg = tr(language, "Could not load your profile. Please try again.", f"خطا در دریافت پروفایل: {me.get('message', 'خطای نامشخص')}")
                    await update.message.reply_text(error_msg)
                    self.handler.remove_pending(sender_id, "analysis")
                    return
                elif "detail" in me:
                    error_msg = tr(language, "Could not load your profile. Please try again.", f"خطا در دریافت پروفایل: {me.get('detail', 'خطای نامشخص')}")
                    await update.message.reply_text(error_msg)
                    self.handler.remove_pending(sender_id, "analysis")
                    return

            if not me or not isinstance(me, dict) or me.get("plan_status") == "expired":
                await update.message.reply_text(
                    tr(language, "⏳ Your plan has expired. Renew it to receive chart analysis.\n✅ News analysis and prices remain free.", "⏳ طرح شما منقضی شده است. برای دریافت تحلیل، لطفاً طرح خود را تمدید کنید.\n✅ تحلیل اخبار و قیمت‌ها همچنان رایگان هستند.")
                )
                self.handler.remove_pending(sender_id, "analysis")
                return

            await self.user.set_state(sender_id, "waiting_for_analysis")

            initial_info_msg_text = tr(language, f"🤖 Starting AI analysis for {symbol}", f"🤖 شروع تحلیل {symbol} توسط هوش مصنوعی")
            await update.message.reply_text(
                text=initial_info_msg_text,
                reply_markup=UserKeyboard.back(language)
            )

            progress_message_text = tr(language, "🤖 Analysis in progress\n⏳ This may take about 2–5 minutes.\n🕒 Please wait.", "🤖 تحلیل در حال انجام است\n⏳ این فرایند ممکن است حدود 2-5 دقیقه زمان ببرد.\n🕒 لطفا منتظر بمانید.")
            try:
                progress_message = await update.message.reply_text(text=progress_message_text)
            except Exception as e:
                print(f"CRITICAL: Failed to send primary Analysis in progress message for {symbol}: {e}.")
                self.handler.remove_pending(sender_id, "analysis")
                await self.user.set_state(sender_id, "")
                return

            task_key = f"analysis_{sender_id}_{symbol}_{int(time.time())}"

            task = asyncio.create_task(
                self.process_analysis_in_background(
                    sender_id, symbol, "crypto_technical_dh", "1y", True,
                    progress_message, update, context, task_key
                )
            )

            self.handler.background_tasks[task_key] = task
            return

        except Exception as e:
            print(f"Error setting up analysis: {str(e)}")
            try:
                await update.message.reply_text(
                    tr(language, f"Could not start the analysis: {str(e)}\nPlease send the symbol again in a moment.", f"خطا در راه‌اندازی تحلیل: {str(e)}\nلطفاً لحظاتی دیگر دوباره نماد را ارسال کنید.")
                )
            except Exception:
                pass
            self.handler.remove_pending(sender_id, "analysis")

    async def process_analysis_in_background(
        self, user_id, symbol, analysis_type, period, show_volume,
        progress_message, update, context, task_key
    ):
        """Process analysis in the background without blocking main handler."""
        try:
            language = (await self.user.get_user(user_id)).get("Language") or "fa"
            progress_text = tr(language, "🤖 Analysis in progress\n⏳ This may take about 2–5 minutes.\n🕒 Please wait.", "🤖 تحلیل در حال انجام است\n⏳ این فرایند ممکن است حدود 2-5 دقیقه زمان ببرد.\n🕒 لطفا منتظر بمانید.")
            
            result = await self.api_request.start_analysis(
                user_id, analysis_type, period, show_volume, symbol, language
            )

            if not result.get("is_task", False):
                await self.handle_analysis_result(result, user_id, symbol, update, context, progress_message)
                self.handler.remove_pending(user_id, "analysis")
                return

            task_id = result.get("task_id")
            if not task_id:
                await update.message.reply_text(tr(language, "Could not retrieve the analysis ID. Please try again.", "خطا در دریافت شناسه تحلیل. لطفا دوباره تلاش کنید."))
                try:
                    await progress_message.delete()
                except Exception:
                    pass
                self.handler.remove_pending(user_id, "analysis")
                return

            try:
                if progress_message:
                    await progress_message.edit_text(progress_text)
            except telegram.error.BadRequest as e:
                error_str = str(e).lower()
                if "message is not modified" in error_str:
                    pass
                elif "message can't be edited" in error_str or "message to edit not found" in error_str:
                    print(f"Error editing progress message for {symbol} (reason: {e}). Attempting to send new one.")
                    try:
                        if update and update.message:
                            progress_message = await update.message.reply_text(progress_text)
                    except Exception as new_msg_e:
                        print(f"Failed to send new progress message for {symbol}: {new_msg_e}")
                else:
                    print(f"Error updating progress message for {symbol}: {e}")
            except Exception as e:
                print(f"Error updating progress message for {symbol}: {e}")
                try:
                    if update and update.message:
                        progress_message = await update.message.reply_text(progress_text)
                except Exception:
                    pass

            max_attempts = 60
            poll_interval = 15

            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)
                status_result = await self.api_request.check_analysis_status(user_id, task_id)

                if not status_result.get("is_task", False):
                    await self.handle_analysis_result(status_result, user_id, symbol, update, context, progress_message)
                    self.handler.remove_pending(user_id, "analysis")
                    return

                poll_interval = min(poll_interval * 1.1, 30)

            try:
                await update.message.reply_text(
                    tr(
                        language,
                        f"⏱️ Analysis for {symbol} is taking longer than expected.\nPlease try again or contact support.",
                        f"⏱️ تحلیل {symbol} بیش از حد معمول طول کشید.\nلطفا مجددا تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    )
                )
                try:
                    await progress_message.delete()
                except Exception:
                    pass
            except Exception as e:
                print(f"Error sending timeout message: {str(e)}")

            self.handler.remove_pending(user_id, "analysis")

        except Exception as e:
            print(f"Error in background analysis task: {str(e)}")
            try:
                await update.message.reply_text(tr(language, f"Analysis failed: {str(e)}", f"خطا در انجام تحلیل: {str(e)}"))
                try:
                    await progress_message.delete()
                except Exception:
                    pass
            except Exception:
                pass
            await self.user.set_state(user_id, "")
            self.handler.remove_pending(user_id, "analysis")

        finally:
            if task_key in self.handler.background_tasks:
                del self.handler.background_tasks[task_key]
            else:
                print(f"Warning: Task key not found for cleanup: {task_key}")

    async def handle_analysis_result(self, analysis, user_id, symbol, update, context, progress_message):
        """Process the analysis result and send appropriate responses."""
        message_success = False
        sending_results_status_msg = None
        try:
            language = (await self.user.get_user(user_id)).get("Language") or "fa"
            if analysis and isinstance(analysis, dict):
                if "error" in analysis and analysis["error"]:
                    last_error = analysis.get('message', tr(language, 'Unknown error', 'خطای نامشخص'))
                    last_status = analysis.get('status')

                    error_message = tr(language, f"Could not retrieve the analysis: {last_error}", f"خطا در دریافت تحلیل: {last_error}")
                    if last_status == 404:
                        error_message = tr(language, "The requested symbol was not found. Please check the symbol and try again.", "نماد مورد نظر یافت نشد. لطفا از درستی نماد اطمینان حاصل کنید.")
                    elif last_status == 401 or last_status == 403:
                        error_message = tr(language, "Analysis access is temporarily unavailable. Please contact support.", "دسترسی به API محدود شده است. لطفا با پشتیبانی تماس بگیرید.")
                    elif last_status == 429:
                        error_message = tr(language, "Too many requests. Please wait a moment and try again.", "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید.")
                    elif last_status and last_status >= 500:
                        error_message = tr(language, "We couldn't generate a valid analysis. Please try again or choose a different symbol.", "تحلیل معتبری تولید نشد. لطفاً دوباره تلاش کنید یا نماد دیگری را انتخاب کنید.")

                    try:
                        await update.message.reply_text(error_message)
                    except Exception as e:
                        print(f"Error sending error message: {str(e)}")

                    try:
                        await progress_message.delete()
                    except Exception:
                        pass

                    await self.user.set_state(user_id, "")
                    return

                elif "detail" in analysis:
                    error_detail = analysis["detail"]
                    if "not found" in error_detail.lower() or "failed" in error_detail.lower():
                        error_message = tr(language, "The symbol was not found or could not be analyzed. Please check it and try again.", "نماد مورد نظر یافت نشد یا تحلیل آن امکان‌پذیر نیست. لطفا از درستی نماد اطمینان حاصل کنید.")
                        await update.message.reply_text(error_message)
                        await progress_message.delete()
                        await self.user.set_state(user_id, "")
                        return

            if "detail" in analysis and "failed" in analysis["detail"]:
                await update.message.reply_text(tr(language, "Could not retrieve the analysis. Please check the symbol and try again.", "خطا در دریافت تحلیل. لطفا درستی نماد وارد شده را بررسی کرده و دوباره ارسال نمایید."))
                await progress_message.delete()
                await self.user.set_state(user_id, "")
                return

            if not analysis.get("images") or not analysis.get("llm_response", {}).get("answer"):
                await update.message.reply_text(tr(language, "The analysis response was incomplete. Please try again.", "تحلیل دریافت شده ناقص است. لطفا دوباره تلاش کنید."))
                await progress_message.delete()
                await self.user.set_state(user_id, "")
                return

            images = analysis["images"]
            caption = analysis["llm_response"]["answer"].strip()

            if progress_message:
                try:
                    await progress_message.delete()
                except Exception as e:
                    print(f"INFO: Could not delete old analysis in progress message: {str(e)}")

            try:
                if update and context:
                    plain_message_text = tr(language, "⏳ Sending analysis results…\nPlease wait.", "⏳ درحال ارسال نتایج تحلیل\nلطفا صبر کنید و از دستورات دیگر استفاده نکنید.")
                    sending_results_status_msg = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=plain_message_text
                    )
            except Exception as e:
                print(f"ERROR: Failed to send sending results status message: {str(e)}")

            await self.user.set_state(user_id, "")

            images_sent_successfully = False

            try:
                if images:
                    media_group = []
                    for i, image_base64 in enumerate(images):
                        try:
                            image_data = base64.b64decode(image_base64)
                            media_group.append(InputMediaPhoto(media=BytesIO(image_data)))
                        except Exception as e:
                            print(f"Error processing image {i} for media group: {str(e)}")

                    if media_group:
                        max_retries = 2
                        for retry in range(max_retries):
                            try:
                                sent_media = await context.bot.send_media_group(
                                    chat_id=update.effective_chat.id,
                                    media=media_group,
                                    read_timeout=60,
                                    write_timeout=60
                                )
                                if sent_media:
                                    images_sent_successfully = True
                                    break
                            except telegram.error.TimedOut as e:
                                print(f"Timeout sending media group (attempt {retry+1}/{max_retries}): {str(e)}")
                                await asyncio.sleep(2)
                            except Exception as e:
                                print(f"Error sending media group (attempt {retry+1}/{max_retries}): {str(e)}")
                                await asyncio.sleep(2)
            except Exception as e:
                print(f"Exception during media group preparation: {str(e)}")

            if not images_sent_successfully and images:
                successful_image_sends = 0
                for i, image_base64 in enumerate(images):
                    max_retries = 2
                    for retry in range(max_retries):
                        try:
                            image_data = base64.b64decode(image_base64)
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=BytesIO(image_data),
                                caption=None,
                                read_timeout=60,
                                write_timeout=60
                            )
                            successful_image_sends += 1
                            break
                        except telegram.error.TimedOut as e:
                            print(f"Timeout sending image {i}: {str(e)}")
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"Error sending image {i}: {str(e)}")
                            await asyncio.sleep(2)

                if successful_image_sends > 0:
                    images_sent_successfully = True

            if caption:
                try:
                    chunks = await self.handler.split_text_by_headings(caption, symbol, user_id, language=language)

                    section_count = await CacheManager.get(f"bot_analysis:{user_id}:{symbol}:count")
                    if not section_count:
                        section_count = len(chunks)
                    else:
                        section_count = int(section_count)

                    if section_count > 1:
                        keyboard = []
                        for i in range(section_count):
                            section_title = await CacheManager.get(f"bot_analysis:{user_id}:{symbol}:title:{i}")
                            if not section_title:
                                section_title = tr(language, f"Section {i+1}", f"بخش {i+1}")

                            if len(section_title) > 25:
                                section_title = section_title[:22] + "..."

                            button_text = section_title + ("✓" if i == 0 else "")
                            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"section_{symbol}_{i}")])

                        reply_markup = InlineKeyboardMarkup(keyboard)

                        if chunks and len(chunks) > 0:
                            try:
                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=chunks[0],
                                    parse_mode=ParseMode.MARKDOWN_V2,
                                    reply_markup=reply_markup
                                )
                                message_success = True
                            except telegram.error.BadRequest as e:
                                if "can't parse entities" in str(e).lower():
                                    try:
                                        plain_text = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', '', chunks[0])
                                        await context.bot.send_message(
                                            chat_id=update.effective_chat.id,
                                            text=plain_text,
                                            reply_markup=reply_markup
                                        )
                                        message_success = True
                                    except Exception as plain_e:
                                        print(f"Error sending plain text: {plain_e}")
                                else:
                                    print(f"Error sending first section: {e}")
                            except Exception as e:
                                print(f"Error sending first section with keyboard: {e}")
                    else:
                        if chunks and len(chunks) > 0:
                            try:
                                await self.handler.send_safe_markdown_message(
                                    context=context,
                                    chat_id=update.effective_chat.id,
                                    text=chunks[0],
                                    reply_markup=None
                                )
                                message_success = True
                            except Exception as e:
                                print(f"Error sending single section: {e}")

                except Exception as e:
                    print(f"Error processing or splitting caption: {str(e)}")
                    try:
                        tagline = tr(language, "Data-driven analysis, not guessing:", "تحلیل مبتنی بر داده، نه حدس:")
                        await self.handler.send_safe_markdown_message(
                            context=context,
                            chat_id=update.effective_chat.id,
                            text=escape(caption) + f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}",
                            reply_markup=None
                        )
                        message_success = True
                    except Exception as text_e:
                        print(f"Error sending fallback text: {str(text_e)}")

            if not images_sent_successfully and not message_success:
                await update.message.reply_text(
                    tr(language, "❌ Failed to send analysis results. Please try again later.", "❌ خطا در ارسال نتایج تحلیل. لطفا بعداً مجدد تلاش کنید."),
                    reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language)
                )
                return

            finished_message = escape(tr(language, "🤖 AI-generated analysis, not financial advice ↑", "🤖 این تحلیل هوش مصنوعی است، نه توصیه مالی ↑"))
            if BOT_RESULTS_CHANNEL:
                results_label = escape(tr(language, "📢 Analysis results & user reviews:", "📢 نتایج تحلیل‌ها و نظرات کاربران:"))
                finished_message += f"\n\n{results_label} {escape(BOT_RESULTS_CHANNEL)}"

            trending = await get_trending_coins()
            if trending:
                selected = random.sample(trending, min(3, len(trending)))
                finished_message += escape(tr(language, "\n\n📡 Chapar radar also flagged these symbols:\n", "\n\n📡 در همین حین، رادار چاپار این نمادها رو علامت‌گذاری کرد:\n"))
                for i, c in enumerate(selected):
                    finished_message += f"{i+1}\\. `{escape(c['symbol'])}`\n"
                finished_message += escape(tr(language, "Want one analyzed? Send its symbol 👇", "تحلیلشون کنم؟ نمادش رو بگو 👇"))

            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=finished_message,
                    reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                print(f"Error sending ending message: {str(e)}")

        except Exception as e:
            print(f"Error processing analysis result: {str(e)}")
            try:
                await update.message.reply_text(
                    "خطا در پردازش نتیجه تحلیل. لطفا مجددا تلاش کنید.",
                    reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language)
                )
            except Exception:
                pass
            await self.user.set_state(user_id, "")
        finally:
            if sending_results_status_msg:
                try:
                    await sending_results_status_msg.delete()
                except Exception as e:
                    print(f"Error deleting sending results status message: {str(e)}")

    async def handle_section_callback(self, update: Update, query, user_id: int, callback_data: str):
        """Handle analysis section navigation callbacks."""
        try:
            parts = callback_data.split("_")
            if len(parts) < 3:
                await query.answer("Invalid section format (internal error)", show_alert=True)
                return

            symbol = parts[1]
            section_index = int(parts[2])
            cache_key = f"bot_analysis:{user_id}:{symbol}:{section_index}"

            cached_text = await CacheManager.get(cache_key)

            if not cached_text:
                await query.answer("تحلیل‌های ارائه شده پس از چند ساعت منقضی می‌شوند. لطفاً تحلیل جدیدی دریافت کنید.", show_alert=True)
                return

            section_count = await CacheManager.get(f"bot_analysis:{user_id}:{symbol}:count")
            if not section_count:
                section_count = 1
            else:
                section_count = int(section_count)

            keyboard = []

            for i in range(section_count):
                section_title = await CacheManager.get(f"bot_analysis:{user_id}:{symbol}:title:{i}")
                if not section_title:
                    section_title = f"بخش {i+1}"

                if len(section_title) > 25:
                    section_title = section_title[:22] + "..."

                button_text = section_title + ("✓" if i == section_index else "")
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"section_{symbol}_{i}")])

            try:
                await query.edit_message_text(
                    text=cached_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except telegram.error.BadRequest as e:
                if "message is not modified" in str(e).lower():
                    pass
                else:
                    try:
                        plain_text = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', '', cached_text)
                        await query.edit_message_text(
                            text=plain_text,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    except Exception as plain_e:
                        print(f"Error editing message as plain text: {plain_e}")
                        await query.answer("خطا در ویرایش پیام.", show_alert=True)

        except Exception as e:
            print(f"Error handling section callback: {str(e)}")
            try:
                await query.answer("خطا در پردازش درخواست شما.", show_alert=True)
            except Exception as e_ans:
                print(f"ERROR: Failed to send error alert: {e_ans}")
        await query.answer()

    async def handle_analyze_callback(self, update: Update, query, user_id: int, callback_data: str, context: ContextTypes.DEFAULT_TYPE):
        """Handle legacy analyze_ callback queries."""
        try:
            parts = callback_data.split("_")
            analyze_method = parts[1]
            period = parts[2]
            show_volume = parts[3] == "true"
            symbol = parts[4]

            user_data = await self.user.get_user(user_id)
            language = user_data.get("Language") or "fa"

            if self.handler.is_pending(user_id):
                await query.message.reply_text(tr(language, "Please wait, your previous request is processing.", "لطفا صبر کنید، درخواست قبلی شما در حال پردازش است."))
                return

            self.handler.add_pending(user_id)

            try:
                progress_message = await query.message.reply_text(tr(language, "Fetching and analyzing data...", "در حال دریافت و تحلیل اطلاعات"))

                result = await self.api_request.analyze(
                    user_id, analyze_method, period, show_volume, symbol
                )

                if not result:
                    await query.message.reply_text(tr(language, "Error fetching data. Please try again.", "خطا در دریافت اطلاعات. لطفا دوباره تلاش کنید."))
                    self.handler.remove_pending(user_id)
                    await progress_message.delete()
                    return

                if isinstance(result, dict):
                    if "error" in result and result["error"]:
                        error_message = f"خطا در دریافت تحلیل: {result.get('message', 'خطای نامشخص')}"
                        error_status = result.get('status')

                        if error_status == 404:
                            error_message = tr(language, "Symbol not found. Please verify the symbol.", "نماد مورد نظر یافت نشد. لطفا از درستی نماد اطمینان حاصل کنید.")
                        elif error_status == 401 or error_status == 403:
                            error_message = tr(language, "API access restricted. Please contact support.", "دسترسی به API محدود شده است. لطفا با پشتیبانی تماس بگیرید.")
                        elif error_status == 429:
                            error_message = tr(language, "Rate limit exceeded. Please wait a moment.", "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید.")
                        elif error_status and error_status >= 500:
                            error_message = tr(language, "Internal server error. Please try again later.", "خطای داخلی سرور. لطفا بعدا مجددا تلاش کنید.")

                        await query.message.reply_text(error_message)
                        self.handler.remove_pending(user_id)
                        await progress_message.delete()
                        return

                    elif "detail" in result:
                        error_detail = result["detail"]
                        if "not found" in error_detail.lower() or "failed" in error_detail.lower():
                            error_message = tr(language, "Symbol not found or cannot be analyzed.", "نماد مورد نظر یافت نشد یا تحلیل آن امکان‌پذیر نیست. لطفا از درستی نماد اطمینان حاصل کنید.")
                            await query.message.reply_text(error_message)
                            self.handler.remove_pending(user_id)
                            await progress_message.delete()
                            return

                if "chart" in result:
                    try:
                        chart_bytes = base64.b64decode(result["chart"])
                        caption = result.get("analysis", tr(language, "Analysis", "تحلیل"))
                        chunks = self.handler.split_text_by_sentences(caption, language=language)

                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=BytesIO(chart_bytes),
                            caption=(chunks[0] if chunks else tr(language, "Analysis in next message", "تحلیل در پیام بعدی")) if len(chunks) == 1 else tr(language, "Analysis in following messages", "تحلیل در پیام‌های بعدی"),
                            parse_mode=ParseMode.MARKDOWN_V2
                        )

                        if len(chunks) > 1:
                            for chunk in chunks[1:]:
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=chunk,
                                    parse_mode=ParseMode.MARKDOWN_V2
                                )

                    except Exception as e:
                        print(f"Error processing chart: {str(e)}")
                        await query.message.reply_text(tr(language, "Error processing chart image. Please try again.", "خطا در پردازش تصویر تحلیل. لطفا مجددا تلاش کنید."))
                        self.handler.remove_pending(user_id)
                        await progress_message.delete()
                        return
                elif "analysis" in result:
                    analysis_text = result.get("analysis", tr(language, "Analysis completed.", "تحلیل انجام شد."))
                    chunks = self.handler.split_text_by_sentences(analysis_text, language=language)
                    for chunk in chunks:
                        await query.message.reply_text(
                            chunk,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                else:
                    await query.message.reply_text(tr(language, "Incomplete response received. Please try again.", "پاسخ دریافتی ناقص است. لطفا دوباره تلاش کنید."))

                self.handler.remove_pending(user_id)
                await progress_message.delete()
            except Exception as e:
                await query.message.reply_text(f"خطا در پردازش تحلیل: {str(e)}")

        except Exception as e:
            await query.message.reply_text(f"خطا در درخواست: {str(e)}")
