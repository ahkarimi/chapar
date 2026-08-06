import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.private_handler import PrivateHandler
from handlers.chart_handler import ChartHandler
from handlers.news_handler import NewsHandler
from handlers.ai_chat_handler import AIChatHandler
from handlers.market_handler import MarketHandler
from handlers.profile_handler import ProfileHandler


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


def test_subhandlers_instantiated(private_handler):
    assert isinstance(private_handler.chart_handler, ChartHandler)
    assert isinstance(private_handler.news_handler, NewsHandler)
    assert isinstance(private_handler.ai_chat_handler, AIChatHandler)
    assert isinstance(private_handler.market_handler, MarketHandler)
    assert isinstance(private_handler.profile_handler, ProfileHandler)


@pytest.mark.asyncio
async def test_chart_handler_symbol_input_validation(private_handler):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Invalid symbol input
    await private_handler.chart_handler.handle_symbol_input(
        update, context, 12345, "invalid!symbol#$", "fa"
    )
    update.message.reply_text.assert_called_once()
    assert "لطفاً یک نماد معتبر وارد کنید" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_news_handler_unsupported_symbol(private_handler):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Symbol not in top 50 / valid news symbols
    await private_handler.news_handler.handle_symbol_input(
        update, context, 12345, "UNKNOWNCOIN", "fa"
    )
    update.message.reply_text.assert_called_once()
    assert "لطفا یک نماد معتبر وارد کنید" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_ai_chat_handler_expired_plan_blocked(private_handler, mock_dbs_and_api):
    _, _, api_request = mock_dbs_and_api
    api_request.me.return_value = {"plan_status": "expired"}

    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.ai_chat_handler.handle_chat_request(
        update, context, 12345, "fa"
    )
    update.message.reply_text.assert_called_once()
    assert "تنها برای کاربران با طرح فعال" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_market_handler_request(private_handler):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    await private_handler.market_handler.handle_market_request(
        update, context, 12345, "fa"
    )
    private_handler.user.set_state.assert_called_with(12345, "analyze")
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_profile_handler_uid_validation(private_handler):
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Non-numeric UID text
    await private_handler.profile_handler.handle_uid_input(
        update, context, 12345, "abc123xyz", "fa"
    )
    update.message.reply_text.assert_called_once_with(
        "لطفا UID را تنها به صورت یک عدد انگلیسی وارد کنید."
    )


@pytest.mark.asyncio
async def test_private_handler_delegation_to_market(private_handler):
    update = MagicMock()
    update.message.date.timestamp.return_value = 1000
    update.message.text = "💰 طلا و دلار"
    update.effective_user.id = 12345
    context = MagicMock()

    with patch.object(private_handler.market_handler, 'handle_market_request', new_callable=AsyncMock) as mock_handle:
        await private_handler.handle_message(update, context)
        mock_handle.assert_called_once()
