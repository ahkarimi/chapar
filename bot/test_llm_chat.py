import asyncio
from types import SimpleNamespace

from database.cache import CacheManager
from tools.llm_chat import LLMChatService


class FakeCompletions:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id=f"message-{len(self.calls)}",
            model=kwargs["model"],
            choices=[SimpleNamespace(message=SimpleNamespace(content="پاسخ آزمایشی"))],
            usage=None,
        )


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_chat_keeps_local_message_history(monkeypatch):
    async def fake_set(*args, **kwargs):
        return None

    monkeypatch.setattr(CacheManager, "set", fake_set)
    client = FakeClient()
    service = LLMChatService(client=client)
    service.model = "provider/chat-model"
    service._history_cache["42"] = []

    async def run_chat():
        first = await service.send_message("سلام", "42")
        await asyncio.sleep(0)
        second = await service.send_message("ادامه بده", "42")
        await asyncio.sleep(0)
        return first, second

    first, second = asyncio.run(run_chat())

    assert first["success"] is True
    assert second["success"] is True
    second_messages = client.chat.completions.calls[1]["messages"]
    assert {"role": "user", "content": "سلام"} in second_messages
    assert {"role": "assistant", "content": "پاسخ آزمایشی"} in second_messages
