"""Reusable admin broadcast behavior."""

import asyncio
import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest


logger = logging.getLogger(__name__)


class BroadcastMixin:
    """Formatting and delivery helpers for administrator broadcasts."""

    def _format_message_text(self, raw_text: str) -> str:
        """Convert a simple shorthand syntax to Telegram HTML.

        Supported shorthands (raw HTML tags are also passed through as-is):
          **text**           →  <b>text</b>
          _text_             →  <i>text</i>
          [label](https://…) →  <a href="…">label</a>

        Any HTML tags that Telegram does NOT support are stripped out.
        """
        text = raw_text

        # **bold** → <b>bold</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)

        # _italic_ → <i>italic</i>
        text = re.sub(r'(?<![_\w])_(.+?)_(?![_\w])', r'<i>\1</i>', text, flags=re.DOTALL)

        # [label](url) → <a href="url">label</a>
        text = re.sub(
            r'\[([^\]]+)\]\((https?://[^\)]+)\)',
            r'<a href="\2">\1</a>',
            text,
        )

        # Strip unsupported HTML tags
        text = self._sanitize_telegram_html(text)

        return text

    @staticmethod
    def _sanitize_telegram_html(text: str) -> str:
        """Remove HTML tags that Telegram's HTML parse mode does not support.

        Allowed tags: b, strong, i, em, u, ins, s, strike, del, tg-spoiler,
        a, code, pre, blockquote.
        """
        if not text:
            return text

        allowed = {
            "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
            "tg-spoiler", "a", "code", "pre", "blockquote",
        }

        def _repl(m: re.Match) -> str:
            # m.group(1) is e.g. "p", "/p", "a href='...'"
            tag_with_attrs = m.group(1).strip()
            tag_name = tag_with_attrs.lower().lstrip("/").split()[0]
            if tag_name in allowed:
                return m.group(0)
            return ""

        return re.sub(r"<(/?[^ >]+)[^>]*>", _repl, text, flags=re.DOTALL)

    def _build_broadcast_keyboard(
        self, button_text: str, button_link: str | None
    ) -> InlineKeyboardMarkup:
        """Build the inline keyboard that accompanies every broadcast.

        If button_link is None the button triggers the /start callback so the
        bot handles it exactly like a fresh /start press.
        """
        if button_link:
            btn = InlineKeyboardButton(text=button_text, url=button_link)
        else:
            btn = InlineKeyboardButton(text=button_text, callback_data="start")
        return InlineKeyboardMarkup([[btn]])

    async def _send_broadcast_to_user(
        self,
        bot,
        user_id: int,
        draft: dict,
        keyboard: InlineKeyboardMarkup,
    ):
        """Deliver a single broadcast message to one user."""
        msg_type = draft.get("type", "text")

        if msg_type == "text":
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=draft["text"],
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            except BadRequest as e:
                if "parse" in str(e).lower() or "entities" in str(e).lower():
                    logger.warning(f"HTML parse error for user {user_id}: {e}. Sending plain text.")
                    await bot.send_message(
                        chat_id=user_id,
                        text=draft["text"],
                        reply_markup=keyboard,
                    )
                else:
                    raise
        else:  # media
            caption = draft.get("caption") or None

            async def _send_media(send_fn, file_id, caption, media_key):
                try:
                    await send_fn(
                        chat_id=user_id,
                        **{media_key: file_id},
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard,
                    )
                except BadRequest as e:
                    if "parse" in str(e).lower() or "entities" in str(e).lower():
                        logger.warning(
                            f"HTML parse error in media caption for user {user_id}: {e}. "
                            "Sending plain caption."
                        )
                        await send_fn(
                            chat_id=user_id,
                            **{media_key: file_id},
                            caption=caption,
                            reply_markup=keyboard,
                        )
                    else:
                        raise

            if draft["media_type"] == "photo":
                await _send_media(bot.send_photo, draft["file_id"], caption, "photo")
            else:  # video
                await _send_media(bot.send_video, draft["file_id"], caption, "video")

    async def broadcast_message(self, draft: dict, bot) -> int:
        """Schedule a background broadcast and return the number of users targeted."""
        users = await self.user.get_all_users()
        total_users = len(users)
        if total_users == 0:
            return 0
        asyncio.create_task(self._process_broadcast(users, draft, bot))
        return total_users

    async def _process_broadcast(self, users: list, draft: dict, bot):
        """Background broadcast with batching and Telegram-safe rate limiting."""
        BATCH_SIZE = 100
        RATE_LIMIT = 1 / 25.0  # ≈25 msgs/sec, safely under Telegram's 30/sec limit

        total_users = len(users)
        sent_count = 0
        failed_count = 0

        keyboard = self._build_broadcast_keyboard(
            draft["button_text"], draft.get("button_link")
        )

        for i in range(0, total_users, BATCH_SIZE):
            batch = users[i : i + BATCH_SIZE]

            for user in batch:
                try:
                    await self._send_broadcast_to_user(
                        bot, user["user_id"], draft, keyboard
                    )
                    sent_count += 1
                    await asyncio.sleep(RATE_LIMIT)
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Broadcast error for {user['user_id']}: {e}")

            # Progress ping every 500 processed users
            if i > 0 and i % 500 == 0 and i + BATCH_SIZE < total_users:
                for admin_id in self.settings.get_admins():
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=(
                                f"⏳ پیشرفت ارسال: {i}/{total_users}\n"
                                f"✅ موفق: {sent_count} | ❌ ناموفق: {failed_count}"
                            ),
                        )
                    except Exception:
                        pass

        # Final report to all admins
        report = (
            f"✅ ارسال همگانی تمام شد!\n\n"
            f"📊 آمار نهایی:\n"
            f"👥 کل کاربران: {total_users}\n"
            f"✅ ارسال موفق: {sent_count}\n"
            f"❌ ارسال ناموفق: {failed_count}"
        )
        for admin_id in self.settings.get_admins():
            try:
                await bot.send_message(chat_id=admin_id, text=report)
            except Exception:
                pass
