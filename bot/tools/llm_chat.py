import asyncio
import json
import logging
from typing import Any, Dict, List

from openai import APIStatusError, APITimeoutError, AsyncOpenAI

from constants import (
    LLM_API_KEY_CHAT,
    LLM_APP_NAME,
    LLM_BASE_URL,
    LLM_CHAT_MODEL,
    LLM_HTTP_REFERER,
    LLM_MAX_HISTORY_MESSAGES,
    LLM_SYSTEM_PROMPT,
    LLM_TIMEOUT,
)
from database.cache import CacheManager

logger = logging.getLogger(__name__)


class LLMChatService:
    """OpenAI-compatible chat service with Redis-backed conversation history."""

    def __init__(self, client: AsyncOpenAI | None = None):
        self.api_url = LLM_BASE_URL
        self.api_key = LLM_API_KEY_CHAT
        self.model = LLM_CHAT_MODEL
        self._history_cache: Dict[str, List[Dict[str, str]]] = {}
        self._cache_max_size = 10000

        headers = {}
        if LLM_HTTP_REFERER:
            headers["HTTP-Referer"] = LLM_HTTP_REFERER
        if LLM_APP_NAME:
            headers["X-OpenRouter-Title"] = LLM_APP_NAME

        self.client = client
        if self.client is None and self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_url.rstrip("/"),
                timeout=LLM_TIMEOUT,
                max_retries=2,
                default_headers=headers,
            )

    def _get_conversation_key(self, user_id: str) -> str:
        return f"llm_conversation:{user_id}"

    async def _get_history(self, user_id: str) -> List[Dict[str, str]]:
        if user_id in self._history_cache:
            return list(self._history_cache[user_id])

        try:
            raw_history = await CacheManager.get(self._get_conversation_key(user_id))
            history = json.loads(raw_history) if raw_history else []
            if not isinstance(history, list):
                history = []
        except (TypeError, ValueError):
            # Discard legacy cache values that are not reusable as message history.
            history = []

        self._history_cache[user_id] = history
        return list(history)

    def _store_history_async(self, user_id: str, history: List[Dict[str, str]]) -> None:
        if len(self._history_cache) >= self._cache_max_size:
            for key in list(self._history_cache)[:1000]:
                self._history_cache.pop(key, None)

        trimmed_history = history[-LLM_MAX_HISTORY_MESSAGES:]
        self._history_cache[user_id] = trimmed_history

        async def _store() -> None:
            try:
                await CacheManager.set(
                    self._get_conversation_key(user_id),
                    json.dumps(trimmed_history, ensure_ascii=False),
                    expire=604800,
                )
            except Exception:
                logger.warning("Failed to persist LLM history for user %s", user_id)

        asyncio.create_task(_store())

    async def clear_conversation_history(self, user_id: str) -> bool:
        try:
            self._history_cache.pop(user_id, None)
            await CacheManager.delete(self._get_conversation_key(user_id))
            return True
        except Exception:
            return False

    async def send_message(self, message: str, user_id: str, language: str = "fa") -> Dict[str, Any]:
        if not self.client or not self.model:
            raise ValueError(
                "LLM_API_KEY (or OPENROUTER_API_KEY) and LLM_MODEL "
                "(or LLM_CHAT_MODEL) must be configured"
            )

        history = await self._get_history(user_id)
        messages: List[Dict[str, str]] = []
        if LLM_SYSTEM_PROMPT:
            messages.append({"role": "system", "content": LLM_SYSTEM_PROMPT})
        messages.append({
            "role": "system",
            "content": "Always answer in English." if language == "en" else "همیشه به زبان فارسی پاسخ بده.",
        })
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            answer = completion.choices[0].message.content if completion.choices else None
            if not answer or not answer.strip():
                return {"success": False, "error": "پاسخ خالی از هوش مصنوعی دریافت شد."}

            answer = answer.strip()
            self._store_history_async(
                user_id,
                history
                + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": answer},
                ],
            )
            usage = getattr(completion, "usage", None)
            return {
                "success": True,
                "answer": answer,
                "metadata": {
                    "model": getattr(completion, "model", self.model),
                    "usage": usage.model_dump() if usage else {},
                },
                "conversation_id": str(user_id),
                "message_id": getattr(completion, "id", None),
            }
        except APITimeoutError:
            logger.error("LLM request timed out for user %s", user_id)
            return {"success": False, "error": "درخواست منقضی شد. لطفاً دوباره تلاش کنید."}
        except APIStatusError as exc:
            logger.error("LLM returned HTTP %s for user %s", exc.status_code, user_id)
            if exc.status_code == 401:
                error = "خطا در احراز هویت سرویس هوش مصنوعی."
            elif exc.status_code == 429:
                error = "درخواست‌ها زیاد است. لطفاً کمی صبر کنید."
            else:
                error = "خطا در ارتباط با سرویس. لطفاً دوباره تلاش کنید."
            return {"success": False, "error": error}
        except Exception as exc:
            logger.exception("LLM request failed for user %s: %s", user_id, exc)
            return {
                "success": False,
                "error": "خطا در ارتباط با هوش مصنوعی. لطفاً دوباره تلاش کنید.",
            }

    async def test_connection(self) -> Dict[str, Any]:
        try:
            response = await self.send_message("سلام", "test_user")
            if response.get("success", False):
                return {"success": True, "message": "LLM API connection successful"}
            return {"success": False, "error": response.get("error", "Unknown error")}
        except Exception as exc:
            return {"success": False, "error": f"Connection test failed: {exc}"}

    async def send_message_streaming(self, message: str, user_id: str, update_callback=None):
        return await self.send_message(message, user_id)
