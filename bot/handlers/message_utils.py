"""Message formatting and shared state helpers for private chats."""

import asyncio
import re

import telegram
from md2tgmd import escape
from telegram.constants import ParseMode

from constants import BOT_BRAND_HANDLE, REDIS_EXPIRE_TIME
from database.cache import CacheManager


from localization import text as tr


class MessageUtilsMixin:
    """Small helpers shared by the private-message workflows."""

    async def send_message_to_admins(self, message, bot):
        """Send a message to all admin users."""
        admins = self.settings.get_admins()
        for admin_id in admins:
            try:
                await bot.send_message(chat_id=admin_id, text=message)
            except Exception as e:
                print(f"Error sending message to admin {admin_id}: {str(e)}")

    def add_pending(self, user_id, request_type="default"):
        """Mark one workflow as pending for a user."""
        self.pending_requests[(user_id, request_type)] = True

    def sanitize_text(self, text):
        """Escape markdown to Telegram MarkdownV2 using md2tgmd."""
        if not isinstance(text, str):
            return text
        return escape(text)

    def split_text_by_sentences(self, text_to_split, max_length=4000, language=None):
        """Split text into chunks by lines up to max_length."""
        if not isinstance(text_to_split, str):
            return []
        lines = text_to_split.split("\n")
        chunks = []
        current_chunk = ""
        tagline = tr(language, "Data-driven analysis, not guessing:", "تحلیل مبتنی بر داده، نه حدس:")
        for line in lines:
            line = escape(line)
            if len(current_chunk) + len(line) + 2 <= max_length:  # +2 for the actual newline
                if current_chunk:
                    # Use actual newline character for Markdown_V2
                    current_chunk = f"{current_chunk}\n{line}"
                else:
                    current_chunk = line
            else:
                chunks.append(current_chunk)
                current_chunk = line
        if current_chunk:
            current_chunk += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"  # Add bot mention in block quotation
            chunks.append(current_chunk)
        return chunks

    async def split_text_by_headings(self, text_to_split, symbol_key, user_id, language=None):
        """
        Split text into chunks by markdown headings (# or ## or ###).
        Each chunk will include its heading and content until the next heading.
        Optionally cache each chunk to Redis if symbol_key is provided.

        Args:
            text_to_split (str): The text to split
            symbol_key (str, optional): Prefix for Redis cache keys. If provided, chunks will be cached.
                                            Format will be bot_analysis:{user_id}:{symbol_key}:{index}
            user_id (int): The user ID to scope the cache per user
            language (str, optional): User's language preference ('en' or 'fa')

        Returns:
            list: List of text chunks split by headings
        """
        if not isinstance(text_to_split, str):
            return []

        tagline = tr(language, "Data-driven analysis, not guessing:", "تحلیل مبتنی بر داده، نه حدس:")

        # Pattern to match markdown headings (# or ## or ### etc.) at the beginning of a line
        # This pattern matches 1-6 # characters followed by at least one space and then text
        heading_pattern_all = r'(?:^|\n)(#{1,6}\s+[^\n]+)'
        all_matches = list(re.finditer(heading_pattern_all, text_to_split))
        # No headings: single chunk
        if not all_matches:
            escaped_text = escape(text_to_split)
            escaped_text += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"
            chunks = [escaped_text]
            if symbol_key:
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:0", escaped_text, expire=REDIS_EXPIRE_TIME)
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:title:0", "تحلیل", expire=REDIS_EXPIRE_TIME)
            return chunks

        # Count headings per level
        level_counts = {}
        level_to_matches = {}
        for m in all_matches:
            heading_line = m.group(1).strip()
            lvl_match = re.match(r'^(#+)', heading_line)
            if not lvl_match:
                continue
            lvl = len(lvl_match.group(1))
            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            level_to_matches.setdefault(lvl, []).append(m)

        # Choose smallest level with multiple occurrences
        splitting_level = None
        for lvl in sorted(level_counts.keys()):
            if level_counts[lvl] > 1:
                splitting_level = lvl
                break
        # Fallback to no-split if none has multiple
        if splitting_level is None:
            escaped_text = escape(text_to_split)
            escaped_text += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"
            chunks = [escaped_text]
            if symbol_key:
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:0", escaped_text, expire=REDIS_EXPIRE_TIME)
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:title:0", "تحلیل", expire=REDIS_EXPIRE_TIME)
            return chunks

        # Split using chosen heading level
        matches = sorted(level_to_matches[splitting_level], key=lambda m: m.start())
        chunks = []
        for i, m in enumerate(matches):
            start_pos = m.start()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(text_to_split)
            section_text = text_to_split[start_pos:end_pos].strip()
            heading_line = m.group(1).strip()
            heading_title = re.sub(r'^#+\s+', '', heading_line).replace('*', '').strip()
            escaped_section = escape(section_text)
            if i != 0:
                escaped_section += f"\n\n> {tagline} {escape(BOT_BRAND_HANDLE)}"
            chunks.append(escaped_section)
            chunks.append(escaped_section)
            if symbol_key:
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:{i}", escaped_section, expire=REDIS_EXPIRE_TIME)
                await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:title:{i}", heading_title, expire=REDIS_EXPIRE_TIME)
        # Cache total count
        if symbol_key:
            await CacheManager.set(f"bot_analysis:{user_id}:{symbol_key}:count", str(len(chunks)), expire=REDIS_EXPIRE_TIME)
        return chunks

    async def send_safe_markdown_message(self, context, chat_id, text, reply_markup=None):
        """
        Tries to send a message with Markdown formatting, falls back to plain text if it fails.

        Args:
            context: The telegram bot context
            chat_id: The chat ID to send the message to
            text: The text message to send
            reply_markup: Optional reply markup

        Returns:
            The message object if successful, None otherwise
        """
        try:
            # First try sending with Markdown formatting
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )
            return message
        except telegram.error.BadRequest as e:
            if "can't parse entities" in str(e).lower():
                print(f"Markdown parsing error. Sending as plain text. Error: {e}")
                try:
                    # Remove markdown special characters
                    plain_text = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', '', text)

                    # Send without markdown formatting
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=plain_text,
                        parse_mode=None,
                        reply_markup=reply_markup
                    )
                    return message
                except Exception as plain_e:
                    print(f"Error sending message as plain text: {plain_e}")
                    return None
            else:
                # For other types of BadRequest errors
                print(f"Other BadRequest error: {e}")
                return None
        except Exception as e:
            print(f"Unexpected error sending message: {e}")
            return None

    def remove_pending(self, user_id, request_type="default"):
        """Clear one pending workflow for a user."""
        self.pending_requests.pop((user_id, request_type), None)

    def is_pending(self, user_id, request_type="default"):
        """Check whether one workflow is pending for a user."""
        return (user_id, request_type) in self.pending_requests

    def get_force_joins(self):
        """Get cached force joins to avoid repeated DB calls"""
        # Cache force_joins for 5 minutes (300 seconds)
        current_time = asyncio.get_event_loop().time()
        if not self._force_joins_cache or current_time - self._force_joins_cache_time > 30000:
            self._force_joins_cache = self.settings.get_force_joins()
            self._force_joins_cache_time = current_time
        return self._force_joins_cache

    async def check_required_channels(self, context, user_id):
        """Allow access while required-channel enforcement is disabled."""
        return True, None

    async def invalidate_membership_cache(self, user_id):
        """Invalidate membership cache for a specific user.

        This should be called when:
        - User clicks "عضو شدم" button
        - We want to force a fresh membership check

        Args:
            user_id: Telegram user ID
        """
        try:
            # Clear overall membership status cache
            membership_cache_key = f"membership_status:{user_id}"
            await CacheManager.delete(membership_cache_key)

            print(f"Cleared membership cache for user {user_id}")
        except Exception as e:
            print(f"Error clearing membership cache for user {user_id}: {e}")
