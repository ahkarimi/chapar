"""Background news-analysis workflow for private chats."""

import asyncio

import telegram

from keyboards import UserKeyboard
from constants import BOT_RESULTS_CHANNEL
from localization import text as tr


def news_completion_message(language, results_channel=None):
    """Build the plain-text footer shown after a news analysis."""
    message = tr(
        language,
        "🤖 AI-generated analysis, not financial advice ↑",
        "🤖 این تحلیل هوش مصنوعی است، نه توصیه مالی ↑",
    )
    if results_channel:
        message += tr(
            language,
            f"\n\n📢 Analysis results and user feedback: {results_channel}",
            f"\n\n📢 نتایج تحلیل‌ها و نظرات کاربران: {results_channel}",
        )
    return message


class NewsWorkflowMixin:
    """Submit news jobs and deliver their eventual results."""

    async def process_news_in_background(
        self, user_id, symbol, method,
        progress_message, update, context, task_key
    ):
        """
        Process news analysis in the background, without blocking the main handler.

        Args:
            user_id: Telegram user ID
            symbol: Stock symbol to analyze news for
            method: News analysis method to use
            progress_message: Message object for the progress indicator
            update: Telegram update object
            context: Telegram context object
            task_key: Unique key for this task in the background_tasks dictionary
        """
        try:
            language = (await self.user.get_user(user_id)).get("Language") or "fa"
            progress_text = tr(language, "🤖 Preparing news analysis\n⏳ This may take about 2–5 minutes.\n🕒 Please wait.", "🤖 در حال دریافت تحلیل اخبار \n⏳ این فرایند ممکن است حدود 2-5 دقیقه زمان ببرد.\n🕒 لطفا منتظر بمانید.")
            # Start the news analysis request - this returns quickly with a task_id
            result = await self.api_request.start_news(
                user_id, symbol, method, language
            )

            # If we got a cached result or error, handle it immediately
            if not result.get("is_task", False):
                await self.handle_news_result(result, user_id, symbol, update, context, progress_message)
                self.remove_pending(user_id, "news")
                return

            # Get the task ID for polling
            task_id = result.get("task_id")
            if not task_id:
                await update.message.reply_text(tr(language, "Could not retrieve the news-analysis ID. Please try again.", "خطا در دریافت شناسه تحلیل اخبار. لطفا دوباره تلاش کنید."))
                try:
                    await progress_message.delete()
                except Exception:
                    pass
                self.remove_pending(user_id, "news")
                return

            # Try to update the progress message, but don't fail if it can't be edited
            try:
                if progress_message: # Ensure progress_message is not None and has an ID
                    await progress_message.edit_text(progress_text)
            except telegram.error.BadRequest as e:
                error_str = str(e).lower()
                if "message is not modified" in error_str:
                    # This is expected in the news flow if the initial message text is the same.
                    pass # print(f"Progress message for news of {symbol} was not modified.")
                elif "message can't be edited" in error_str or "message to edit not found" in error_str:
                    print(f"Error editing news progress message for {symbol} (reason: {e}). Attempting to send a new one.")
                    try:
                        if update and update.message: # Ensure update and message objects are valid
                            progress_message = await update.message.reply_text(progress_text)
                        else:
                            print(f"Cannot send new news progress message for {symbol}: update or update.message is invalid.")
                    except Exception as new_msg_e:
                        print(f"Failed to send new news progress message for {symbol} after edit failed: {new_msg_e}")
                else:
                    # Other BadRequest errors
                    print(f"Error updating news progress message for {symbol} (BadRequest): {e}")
            except Exception as e:
                # General errors
                print(f"Error updating news progress message for {symbol} (General Exception): {e}")
                try:
                    if update and update.message: # Ensure update and message objects are valid
                        progress_message = await update.message.reply_text(progress_text)
                    else:
                        print(f"Cannot send new news progress message for {symbol}: update or update.message is invalid.")
                except Exception as new_msg_e:
                    print(f"Failed to send new news progress message for {symbol} after edit failed (General Exception): {new_msg_e}")

            # Start polling for the result
            max_attempts = 60  # Maximum number of polling attempts
            poll_interval = 5   # Initial polling interval in seconds

            for attempt in range(max_attempts):
                # Wait before polling
                await asyncio.sleep(poll_interval)

                # Check the task status
                status_result = await self.api_request.check_news_status(user_id, task_id)

                # If it's no longer a task (completed or failed), process the result
                if not status_result.get("is_task", False):
                    await self.handle_news_result(status_result, user_id, symbol, update, context, progress_message)
                    self.remove_pending(user_id, "news")
                    return

                # Increase the poll interval for longer wait times (max 15 seconds)
                poll_interval = min(poll_interval * 1.1, 15)

            # If we've exhausted all polling attempts
            try:
                await update.message.reply_text(
                    tr(
                        language,
                        f"⏱️ News analysis for {symbol} is taking longer than expected.\nPlease try again or contact support.",
                        f"⏱️ تحلیل اخبار {symbol} بیش از حد معمول طول کشید.\nلطفا مجددا تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    )
                )
                try:
                    await progress_message.delete()
                except Exception:
                    pass
            except Exception as e:
                print(f"Error sending timeout message: {str(e)}")

            self.remove_pending(user_id, "news")

        except Exception as e:
            # Handle any exceptions in the background task
            print(f"Error in background news task: {str(e)}")
            try:
                await update.message.reply_text(tr(language, f"News analysis failed: {str(e)}", f"خطا در انجام تحلیل اخبار: {str(e)}"))
                try:
                    await progress_message.delete()
                except Exception:
                    pass
            except Exception:
                pass
            # Restore user state to the main menu when an error occurs
            await self.user.set_state(user_id, "")
            self.remove_pending(user_id, "news")

        finally:
            # Clean up the task reference to prevent memory leaks
            if task_key in self.background_tasks:
                del self.background_tasks[task_key]
            else:
                print(f"Warning: Task key not found for cleanup: {task_key}")

    async def handle_news_result(self, analysis, user_id, symbol, update, context, progress_message):
        """
        Process the news analysis result and send appropriate responses.

        Args:
            analysis: News analysis result from API
            user_id: Telegram user ID
            symbol: Stock symbol that was analyzed
            update: Telegram update object
            context: Telegram context object
            progress_message: Message object for the progress indicator
        """
        try:
            language = (await self.user.get_user(user_id)).get("Language") or "fa"
            # Check for various error patterns in the response
            if analysis and isinstance(analysis, dict):
                # Explicit error flag
                if "error" in analysis and analysis["error"]:
                    last_error = analysis.get('message', tr(language, 'Unknown error', 'خطای نامشخص'))
                    last_status = analysis.get('status')

                    # Format specific error message based on status
                    error_message = tr(language, f"Could not retrieve the news analysis: {last_error}", f"خطا در دریافت تحلیل اخبار: {last_error}")
                    if last_status == 404:
                        error_message = tr(language, "The requested symbol was not found. Please check the symbol and try again.", "نماد مورد نظر یافت نشد. لطفا از درستی نماد اطمینان حاصل کنید.")
                    elif last_status == 401 or last_status == 403:
                        error_message = tr(language, "News-analysis access is temporarily unavailable. Please contact support.", "دسترسی به API محدود شده است. لطفا با پشتیبانی تماس بگیرید.")
                    elif last_status == 429:
                        error_message = tr(language, "Too many requests. Please wait a moment and try again.", "تعداد درخواست های شما بیش از حد مجاز است. لطفا کمی صبر کنید.")
                    elif last_status and last_status >= 500:
                        error_message = tr(language, "We couldn't generate the news analysis. Please try again or choose a different symbol.", "تحلیل اخبار تولید نشد. لطفاً دوباره تلاش کنید یا نماد دیگری را انتخاب کنید.")

                    try:
                        await update.message.reply_text(error_message)
                    except Exception as e:
                        print(f"Error sending error message: {str(e)}")

                    try:
                        await progress_message.delete()
                    except Exception:
                        pass

                    # Reset state to main menu on error
                    await self.user.set_state(user_id, "")
                    return

                # Error in detail field
                elif "detail" in analysis:
                    error_detail = analysis["detail"]
                    if "not found" in error_detail.lower() or "failed" in error_detail.lower():
                        error_message = tr(language, "The symbol was not found or could not be analyzed. Please check it and try again.", "نماد مورد نظر یافت نشد یا تحلیل آن امکان‌پذیر نیست. لطفا از درستی نماد اطمینان حاصل کنید.")
                        await update.message.reply_text(error_message)
                        await progress_message.delete()
                        # Reset state to main menu on error
                        await self.user.set_state(user_id, "")
                        return

            if "detail" in analysis and "failed" in analysis["detail"]:
                await update.message.reply_text(tr(language, "Could not retrieve the news analysis. Please check the symbol and try again.", "خطا در دریافت تحلیل اخبار. لطفا درستی نماد وارد شده را بررسی کرده و دوباره ارسال نمایید."))
                await progress_message.delete()
                # Reset state to main menu on error
                await self.user.set_state(user_id, "")
                return

            # Check for required fields in the response
            if not analysis.get("news", {}).get("answer"):
                await update.message.reply_text(tr(language, "The news-analysis response was incomplete. Please try again.", "تحلیل اخبار دریافت شده ناقص است. لطفا دوباره تلاش کنید."))
                await progress_message.delete()
                # Reset state to main menu on error
                await self.user.set_state(user_id, "")
                return

            caption = analysis["news"]["answer"]
            caption = caption.replace("```", "")
            caption = caption.strip()

            # Reset user state
            await self.user.set_state(user_id, "")

            # Always split text into chunks using our utility function
            chunks = self.split_text_by_sentences(caption, language=language)

            # Send each chunk with our safe markdown function
            for chunk in chunks:
                await self.send_safe_markdown_message(
                    context=context,
                    chat_id=user_id,
                    text=chunk,
                    reply_markup=None
                )

            # Send completion message
            finished_message = news_completion_message(language, BOT_RESULTS_CHANNEL)

            # Send keyboard after the last message
            await context.bot.send_message(
                chat_id=user_id,
                text=finished_message,
                reply_markup=UserKeyboard.main(self.settings.is_admin(user_id), language),
            )

            # Delete progress message
            await progress_message.delete()

        except Exception as e:
            print(f"News analysis result handling error: {str(e)}")
            try:
                await update.message.reply_text(tr(language, "An error occurred while processing the news analysis.", "خطایی در پردازش تحلیل اخبار رخ داد."))
                await progress_message.delete()
            except Exception:
                pass
            # Reset state to main menu on error
            await self.user.set_state(user_id, "")
