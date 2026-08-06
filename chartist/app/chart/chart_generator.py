# app/charts.py
import io
import hashlib
import json
import base64
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from mplchart.chart import Chart
from mplchart.primitives import Candlesticks, Volume
from mplchart.indicators import SMA, EMA, ROC, RSI, MACD, BBANDS, ADX, MFI
from app.chart.indicators.vwap import VWAP
from app.schemas.chart import ChartRequest, FileFormat
from app.core.cache import CacheManager
from app.core.json_loader import load_json_file
from app.config import settings
from app.providers.market_data_provider import MarketDataProvider
import pickle
import logging

# Get logger for this module
logger = logging.getLogger(__name__)


class ChartGenerator:
    # Valid periods and intervals as class constants
    VALID_PERIODS = frozenset(
        ["1d", "5d", "1m", "3m", "6m", "1y", "2y", "5y", "10y", "ytd", "max"]
    )

    VALID_INTERVALS = frozenset(
        [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "1w",
            "1M",
        ]
    )

    # Smart mapping of periods to intervals (now a constant dictionary)
    PERIOD_TO_INTERVAL = {
        "1d": "1m",  # For 1 day, use 1-minute intervals
        "5d": "5m",  # For 5 days, use 5-minute intervals
        "1m": "30m",  # For 1 month, use 30-minute intervals
        "3m": "1h",  # For 3 months, use 1-hour intervals
        "6m": "6h",  # For 6 months, use 6-hour intervals
        "1y": "1d",  # For 1 year, use daily intervals
        "2y": "1d",  # For 2 years, use daily intervals
        "5y": "1w",  # For 5 years, use weekly intervals
        "10y": "1w",  # For 10 years, use weekly intervals
        "ytd": "1d",  # For year-to-date, use daily intervals
        "max": "1M",  # For maximum period, use monthly intervals
    }

    # Default chart style
    DEFAULT_STYLE = {
        "background_color": "#ffffff",
        "grid_color": "#E6E6E6",
        "text_color": "#333333",
        "border_color": "#666666",
    }

    def __init__(self, data_provider: MarketDataProvider):
        self.data_provider = data_provider
        self._configure_plot_defaults()
        # Load settings from data.json instead of YAML
        try:
            self.data = load_json_file("data.json")
            # Get the chart expiration time from JSON data, default to 3600 (1 hour)
            self.chart_expire = self.data.get("redis_expiration", {}).get("chart", 3600)
        except Exception as e:
            print(f"Warning: Failed to load data from JSON file: {e}")
            self.chart_expire = 3600  # Default to 1 hour if loading fails

    def _configure_plot_defaults(self) -> None:
        """Configure default matplotlib parameters."""
        plt.rcParams.update(
            {
                "figure.figsize": [12, 8],
                "figure.dpi": 300,
                "font.size": 10,
                "axes.titlesize": 12,
                "axes.labelsize": 10,
            }
        )

    def _generate_cache_key(self, request: ChartRequest) -> str:
        """Generate a cache key for chart requests."""
        request_data = json.dumps(request.model_dump(), sort_keys=True)
        return hashlib.md5(request_data.encode()).hexdigest()

    @lru_cache(maxsize=128)
    def _get_smart_interval(
        self,
        period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Determine the appropriate interval based on the period or date range.
        """
        if start_date and end_date:
            days = (end_date - start_date).days
            # Using a more precise interval selection
            if days <= 1:
                return "1m"
            elif days <= 7:
                return "5m"
            elif days <= 30:
                return "30m"
            elif days <= 90:
                return "1h"
            elif days <= 365:
                return "1d"
            elif days <= 365 * 2:
                return "1d"
            elif days <= 365 * 5:
                return "1w"
            return "1M"

        return self.PERIOD_TO_INTERVAL[period]

    def _validate_request(
        self, symbol: str, period: str, interval: Optional[str]
    ) -> None:
        """Validate symbol, period, and interval parameters."""
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")
        if not symbol.replace(".", "").replace("-", "").isalnum():
            raise ValueError("Invalid symbol format")
        if period not in self.VALID_PERIODS:
            raise ValueError(
                f"Invalid period: {period}. Valid periods are: {', '.join(sorted(self.VALID_PERIODS))}"
            )
        if interval and interval not in self.VALID_INTERVALS:
            raise ValueError(
                f"Invalid interval: {interval}. Valid intervals are: {', '.join(sorted(self.VALID_INTERVALS))}"
            )

    def _generate_smart_title(
        self, symbol: str, period: str, interval: str, indicators: list
    ) -> str:
        """
        Generate a smart, descriptive title for the chart.

        Args:
            symbol (str): Stock symbol
            period (str): Time period
            interval (str): Data interval
            indicators (list): List of technical indicators

        Returns:
            str: Formatted chart title
        """
        # Format period for display
        period_display = {
            "1d": "1 Day",
            "5d": "5 Days",
            "1m": "1 Month",
            "3m": "3 Months",
            "6m": "6 Months",
            "1y": "1 Year",
            "2y": "2 Years",
            "5y": "5 Years",
            "10y": "10 Years",
            "ytd": "Year to Date",
            "max": "Maximum",
        }.get(period, period)

        # Format interval for display
        interval_display = {
            "1m": "1 Minute",
            "3m": "3 Minutes",
            "5m": "5 Minutes",
            "15m": "15 Minutes",
            "30m": "30 Minutes",
            "1h": "1 Hour",
            "2h": "2 Hours",
            "4h": "4 Hours",
            "6h": "6 Hours",
            "8h": "8 Hours",
            "12h": "12 Hours",
            "1d": "Daily",
            "1w": "Weekly",
            "1M": "Monthly",
        }.get(interval, interval)

        # Get indicator names
        indicator_names = []
        for ind in indicators:
            if isinstance(ind, SMA):
                indicator_names.append(f"SMA({ind.period})")
            elif isinstance(ind, EMA):
                indicator_names.append(f"EMA({ind.period})")
            elif isinstance(ind, RSI):
                indicator_names.append("RSI")
            elif isinstance(ind, MACD):
                indicator_names.append("MACD")
            elif isinstance(ind, ROC):
                indicator_names.append(f"ROC({ind.period})")
            elif isinstance(ind, VWAP):
                indicator_names.append("VWAP")

        # Create indicator string if any indicators are present
        indicator_string = (
            f" with {', '.join(indicator_names)}" if indicator_names else ""
        )

        return (
            f"{symbol} - {period_display} Chart ({interval_display}{indicator_string})"
        )

    def _get_stock_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Any:
        interval = interval or self._get_smart_interval(period, start_date, end_date)
        data = self.data_provider.get_data(
            symbol, period, interval, start_date, end_date
        )
        return data, interval

    def _create_indicators(self, request: ChartRequest) -> list:
        """Create list of indicators based on request parameters."""
        indicators = [Candlesticks()]

        if request.show_volume:
            indicators.append(Volume())

        # Add technical indicators
        indicators.extend([SMA(period) for period in request.sma_periods])
        indicators.extend([EMA(period) for period in request.ema_periods])

        if request.show_rsi:
            indicators.append(RSI())
        if request.show_macd:
            indicators.append(MACD())
        if request.show_roc:
            indicators.append(ROC(request.roc_period))
        if request.show_vwap:
            indicators.append(VWAP())
        if request.show_bbands:
            indicators.append(BBANDS())
        if request.show_adx:
            indicators.append(ADX())
        if request.show_mfi:
            indicators.append(MFI())

        return indicators

    def _apply_chart_style(
        self, chart: Chart, style_dict: Optional[Dict] = None
    ) -> None:
        """Apply custom style to chart."""
        style_to_apply = {**self.DEFAULT_STYLE, **(style_dict or {})}

        for key, value in style_to_apply.items():
            setattr(chart, key, value)

    def _add_watermark(self, request: ChartRequest) -> None:
        """Add watermark to the chart if specified."""
        if request.watermark_text:
            plt.figtext(
                0.5,
                0.5,
                request.watermark_text,
                fontsize=request.watermark_fontsize or 30,
                color=request.watermark_color or "#CCCCCC",
                alpha=request.watermark_alpha or 0.3,
                ha="center",
                va="center",
                rotation=0,
            )

    def _set_dynamic_yticks(self, ax, max_major_ticks=16, max_minor_per_interval=5):
        """
        Set dynamic y-axis ticks for better readability.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The Axes whose y-axis you want to retick.
        max_major_ticks : int
            The maximum number of major ticks to show. Fewer will be used if that better fits "nice" numbers.
        max_minor_per_interval : int
            How many minor ticks to place *between* each pair of major ticks.
        """
        # Choose nice major ticks (MaxNLocator picks integer multiples of 1,2,5,10…)
        maj = mticker.MaxNLocator(nbins=max_major_ticks, prune=None)
        ax.yaxis.set_major_locator(maj)

        # AutoMinorLocator will insert up to N minors in each major interval
        if max_minor_per_interval > 0:
            minor = mticker.AutoMinorLocator(n=max_minor_per_interval + 1)
            ax.yaxis.set_minor_locator(minor)

        # Configure tick labels - major on left, minor (if any) on right
        ax.tick_params(axis='y',
                    which='major',
                    labelleft=False, labelright=True)
        ax.tick_params(axis='y',
                    which='minor',
                    labelleft=False, labelright=True,
                    length=6)  # shorter minor ticks

    def _save_chart(self, request: ChartRequest) -> Tuple[bytes, str, str]:
        """Save chart to bytes buffer in requested format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{timestamp}.{request.file_format.value}"

        content_types = {
            FileFormat.PNG: "image/png",
            FileFormat.JPEG: "image/jpeg",
            FileFormat.SVG: "image/svg+xml",
            FileFormat.PDF: "application/pdf",
        }

        fig = plt.gcf()  # Get the active figure

        # Check if the figure has data
        if not fig.axes or not any(ax.has_data() for ax in fig.axes):
            raise ValueError("Cannot save an empty figure. No data in axes.")

        # Calculate dpi to enforce maximum size of 2048x2048 pixels.
        max_size = 2048  # Max dimension in pixels
        fig_width, fig_height = fig.get_size_inches()
        dpi = min(
            300, max_size / max(fig_width, fig_height)
        )  # Adjust dpi to fit within bounds

        save_params = {
            "bbox_inches": "tight",
            "format": request.file_format.value,
            "dpi": dpi
            if request.file_format in (FileFormat.PNG, FileFormat.JPEG)
            else None,
        }

        # Remove None values from save_params
        save_params = {k: v for k, v in save_params.items() if v is not None}

        with io.BytesIO() as buf:
            try:
                plt.savefig(buf, **save_params)
            except IndexError as e:
                raise RuntimeError("Failed to save figure due to empty data.") from e
            buf.seek(0)
            chart_bytes = buf.getvalue()

        return chart_bytes, filename, content_types[request.file_format]

    async def generate_chart(self, request: ChartRequest) -> Tuple[bytes, str, str]:
        """Generate stock chart based on request parameters."""

        cache_key = self._generate_cache_key(request)

        # First, try to retrieve the chart from the Redis cache
        cached_chart = await CacheManager.get(cache_key)
        if cached_chart:
            # Decode the cached Base64 data to bytes
            try:
                cached_chart_data = json.loads(cached_chart)
                chart_bytes = base64.b64decode(cached_chart_data["chart_bytes"])
                filename = cached_chart_data["filename"]
                content_type = cached_chart_data["content_type"]
                return chart_bytes, filename, content_type
            except KeyError as e:
                raise ValueError(f"Error decoding cached chart data: {str(e)}")
            except Exception as e:
                raise ValueError(f"Error retrieving cached chart: {str(e)}")

        try:
            interval_value = (
                request.interval.value if request.interval is not None else None
            )
            period_value = request.period.value if request.period is not None else None

            # Define a cache key for stock data
            stock_cache_key = f"stock_price_data:{request.symbol}:{period_value}:{interval_value}:{request.start_date}:{request.end_date}"

            # Attempt to retrieve cached stock data
            cached_stock_data = await CacheManager.get(stock_cache_key)
            if cached_stock_data:
                try:
                    stock_data = json.loads(cached_stock_data)
                    serialized_prices = stock_data["prices"]
                    prices = pickle.loads(base64.b64decode(serialized_prices))
                    actual_interval = stock_data["actual_interval"]

                except Exception:
                    # If there's an error, proceed to fetch fresh data
                    prices, actual_interval = self._get_stock_data(
                        request.symbol,
                        period_value,
                        interval_value,
                        request.start_date,
                        request.end_date,
                    )
                    # Cache the freshly retrieved stock data
                    stock_data = {"prices": prices, "actual_interval": actual_interval}
                    await CacheManager.set(
                        stock_cache_key, json.dumps(stock_data), expire=self.chart_expire
                    )
            else:
                # If not cached, fetch the stock data
                prices, actual_interval = self._get_stock_data(
                    request.symbol,
                    period_value,
                    interval_value,
                    request.start_date,
                    request.end_date,
                )
                serialized_prices = base64.b64encode(pickle.dumps(prices)).decode(
                    "utf-8"
                )
                stock_data = {
                    "prices": serialized_prices,
                    "actual_interval": actual_interval,
                }
                # Cache the stock data for future requests
                await CacheManager.set(
                    stock_cache_key, json.dumps(stock_data), expire=self.chart_expire
                )

            # Create indicators
            indicators = self._create_indicators(request)
            if not indicators:
                raise ValueError("No indicators configured for the chart")

            # Generate smart title
            smart_title = self._generate_smart_title(
                request.symbol, request.period, actual_interval, indicators
            )

            # Create and configure chart
            chart = Chart(title=request.title or smart_title, max_bars=request.max_bars)

            # Apply style
            self._apply_chart_style(chart, request.style_dict)

            # Plot the chart
            chart.plot(prices, indicators)

            # Apply dynamic y-ticks to the main price axes if requested
            if getattr(request, 'use_dynamic_yticks', False):
                max_major_ticks = getattr(request, 'max_major_yticks', 10)
                max_minor_per_interval = getattr(request, 'max_minor_per_interval', 5)
                ax_price = chart.main_axes()
                self._set_dynamic_yticks(ax_price, max_major_ticks, max_minor_per_interval)

            # Add watermark if specified
            self._add_watermark(request)

            # Save the chart to bytes
            chart_bytes, filename, content_type = self._save_chart(request)

            # Cache the chart bytes as Base64 string
            cached_chart_data = {
                "chart_bytes": base64.b64encode(chart_bytes).decode("utf-8"),
                "filename": filename,
                "content_type": content_type,
            }
            await CacheManager.set(
                cache_key,
                json.dumps(cached_chart_data),
                expire=self.chart_expire,
            )

            return chart_bytes, filename, content_type

        except Exception as e:
            raise ValueError(f"Error generating chart: {str(e)}")
