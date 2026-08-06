import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.providers.market_data_provider import MarketDataProvider, BaseExchangeProvider
from app.providers.toobit_data_provider import ToobitDataProvider
from app.providers.bourse_provider import SourcearenaDataProvider
from app.providers.yahoo_data_provider import YahooDataProvider
from app.providers.binance_data_provider import BinanceDataProvider
from app.providers.fallback_provider import FallbackMarketDataProvider
from app.providers.factory import get_provider, get_provider_for_symbol
from app.services.chart_service import ChartService


def test_interface_and_inheritance():
    """Verify that all providers subclass BaseExchangeProvider / MarketDataProvider."""
    assert issubclass(MarketDataProvider, BaseExchangeProvider)
    assert issubclass(ToobitDataProvider, BaseExchangeProvider)
    assert issubclass(SourcearenaDataProvider, BaseExchangeProvider)
    assert issubclass(YahooDataProvider, BaseExchangeProvider)
    assert issubclass(BinanceDataProvider, BaseExchangeProvider)
    assert issubclass(FallbackMarketDataProvider, BaseExchangeProvider)


def test_binance_data_provider_transformation():
    """Test BinanceDataProvider data fetching and DataFrame formatting."""
    provider = BinanceDataProvider()
    mock_raw_klines = [
        [
            1700000000000,
            "100.0",
            "110.0",
            "95.0",
            "105.0",
            "50.0",
            1700000060000,
            "5000.0",
            100,
            "25.0",
            "2500.0",
            "0",
        ]
    ]

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_raw_klines
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        df = provider.get_data(symbol="BTCUSDT", period="1d", interval="1d")
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["open", "close", "high", "low", "volume"]
        assert df.index.name == "date"
        assert df.iloc[0]["open"] == 100.0
        assert df.iloc[0]["close"] == 105.0


def test_yahoo_data_provider_transformation():
    """Test YahooDataProvider standardizing capitalized yfinance columns to lowercase."""
    provider = YahooDataProvider()
    mock_history_df = pd.DataFrame(
        {
            "Open": [10.0],
            "High": [12.0],
            "Low": [9.0],
            "Close": [11.0],
            "Volume": [1000],
        },
        index=pd.date_range("2026-01-01", periods=1),
    )

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_history_df
        mock_ticker_cls.return_value = mock_ticker

        df = provider.get_data(symbol="AAPL", period="1y", interval="1d")
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["open", "close", "high", "low", "volume"]
        assert df.index.name == "date"
        assert df.iloc[0]["open"] == 10.0


def test_fallback_provider_success_primary():
    """Test FallbackMarketDataProvider when primary succeeds."""
    primary = MagicMock(spec=MarketDataProvider)
    fallback = MagicMock(spec=MarketDataProvider)
    expected_df = pd.DataFrame({"open": [1.0], "close": [2.0]})
    primary.get_data.return_value = expected_df

    adapter = FallbackMarketDataProvider(primary=primary, fallback=fallback)
    result = adapter.get_data("BTCUSDT", "1d", "1d")

    assert result is expected_df
    primary.get_data.assert_called_once()
    fallback.get_data.assert_not_called()


def test_fallback_provider_switch_on_error():
    """Test FallbackMarketDataProvider when primary raises an error."""
    primary = MagicMock(spec=MarketDataProvider)
    fallback = MagicMock(spec=MarketDataProvider)
    primary.get_data.side_effect = RuntimeError("Primary API down")

    fallback_df = pd.DataFrame({"open": [1.0], "close": [2.0]})
    fallback.get_data.return_value = fallback_df

    adapter = FallbackMarketDataProvider(primary=primary, fallback=fallback)
    result = adapter.get_data("BTCUSDT", "1d", "1d")

    assert result is fallback_df
    primary.get_data.assert_called_once()
    fallback.get_data.assert_called_once()


def test_fallback_provider_both_failed():
    """Test FallbackMarketDataProvider when both primary and fallback fail."""
    primary = MagicMock(spec=MarketDataProvider)
    fallback = MagicMock(spec=MarketDataProvider)
    primary.get_data.side_effect = RuntimeError("Primary API down")
    fallback.get_data.side_effect = RuntimeError("Fallback API down")

    adapter = FallbackMarketDataProvider(primary=primary, fallback=fallback)
    with pytest.raises(RuntimeError, match="Fallback API down"):
        adapter.get_data("BTCUSDT", "1d", "1d")


def test_provider_factory_resolution():
    """Test get_provider and get_provider_for_symbol."""
    binance_p = get_provider("binance")
    assert isinstance(binance_p, BinanceDataProvider)

    yahoo_p = get_provider("yahoo")
    assert isinstance(yahoo_p, YahooDataProvider)

    # Non-persian symbol => default toobit + fallback binance
    crypto_provider = get_provider_for_symbol("BTCUSDT")
    assert isinstance(crypto_provider, FallbackMarketDataProvider)
    assert isinstance(crypto_provider.primary, ToobitDataProvider)
    assert isinstance(crypto_provider.fallback, BinanceDataProvider)

    # Persian symbol => default sourcearena + fallback yahoo
    persian_provider = get_provider_for_symbol("خودرو")
    assert isinstance(persian_provider, FallbackMarketDataProvider)
    assert isinstance(persian_provider.primary, SourcearenaDataProvider)
    assert isinstance(persian_provider.fallback, YahooDataProvider)


def test_chart_service_provider_selection():
    """Test ChartService select_data_provider integration."""
    service = ChartService()
    service.select_data_provider("BTCUSDT")
    assert isinstance(service.data_provider, FallbackMarketDataProvider)

    # With override provider
    custom_provider = BinanceDataProvider()
    override_service = ChartService(data_provider=custom_provider)
    override_service.select_data_provider("BTCUSDT")
    assert override_service.data_provider is custom_provider
