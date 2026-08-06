import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.private_handler import PrivateHandler
from constants import (
    is_ai_chat_configured,
    is_chart_analysis_configured,
    is_news_analysis_configured,
    is_toobit_verification_configured,
)


@pytest.fixture
def mock_dbs_and_api():
    user_db = AsyncMock()
    user_db.get_user.return_value = {"State": "", "Language": "fa"}
    settings_db = MagicMock()
    settings_db.is_admin.return_value = False
    settings_db.get_toobit_invitation_link.return_value = "https://toobit.com/ref"
    api_request = AsyncMock()
    api_request.me.return_value = {
        "id": 12345,
        "name": "Test User",
        "plan_status": "active",
        "total_requests": 10,
        "remaining_time_human": "5 روز",
        "plan_end_date_human": "1403/05/10",
    }
    return user_db, settings_db, api_request


@pytest.fixture
def private_handler(mock_dbs_and_api):
    user_db, settings_db, api_request = mock_dbs_and_api
    return PrivateHandler(user_db, settings_db, api_request)


def test_key_checkers_detect_missing_and_present_keys(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY_CHAT", "")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("TOOBIT_API_KEY", "")
    monkeypatch.setenv("EXCHANGE_INVITATION_LINK", "")

    assert is_ai_chat_configured() is False
    assert is_chart_analysis_configured() is False
    assert is_news_analysis_configured() is False
    assert is_toobit_verification_configured() is False

    monkeypatch.setenv("LLM_API_KEY", "test-llm-key")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-brave-key")
    monkeypatch.setenv("TOOBIT_API_KEY", "test-toobit-key")
    monkeypatch.setenv("EXCHANGE_INVITATION_LINK", "https://toobit.com/invite")

    assert is_ai_chat_configured() is True
    assert is_chart_analysis_configured() is True
    assert is_news_analysis_configured() is True
    assert is_toobit_verification_configured() is True


@pytest.mark.asyncio
async def test_ai_chat_missing_key_warning(private_handler, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY_CHAT", "")

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.ai_chat_handler.handle_chat_request(update, context, 12345, "fa")

    update.message.reply_text.assert_called_once()
    assert "کلید API یافت نشد" in update.message.reply_text.call_args[0][0]
    private_handler.user.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_chart_analysis_missing_key_warning(private_handler, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.chart_handler.handle_chart_request(update, context, 12345, "fa")

    update.message.reply_text.assert_called_once()
    assert "عدم تنظیم کلید API" in update.message.reply_text.call_args[0][0]
    private_handler.user.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_news_analysis_missing_key_warning(private_handler, monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.news_handler.handle_news_request(update, context, 12345, "fa")

    update.message.reply_text.assert_called_once()
    assert "عدم تنظیم کلیدهای API" in update.message.reply_text.call_args[0][0]
    private_handler.user.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_profile_toobit_missing_key_warning(private_handler):
    private_handler.settings.get_toobit_invitation_link.return_value = None

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.profile_handler.handle_free_credit_request(update, context, 12345, "fa")

    update.message.reply_text.assert_called_once()
    assert "لینک دعوت توبیت یافت نشد" in update.message.reply_text.call_args[0][0]
    private_handler.user.set_state.assert_not_called()
