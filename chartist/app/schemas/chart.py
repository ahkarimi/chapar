from enum import Enum
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class FileFormat(str, Enum):
    """Supported file formats for chart output."""

    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    PDF = "pdf"


class ChartPeriod(str, Enum):
    """Valid time periods for historical data."""

    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    YEAR_TO_DATE = "ytd"
    MAXIMUM = "max"


class ChartInterval(str, Enum):
    """Valid intervals for data points."""

    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOUR = "2h"
    FOUR_HOUR = "4h"
    SIX_HOUR = "6h"
    EIGHT_HOUR = "8h"
    TWELVE_HOUR = "12h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class ChartRequest(BaseModel):
    """Schema for chart generation requests with optional parameters and smart defaults."""

    # Required parameters
    symbol: str = Field(
        ...,
        description="Stock symbol (e.g., BTCUSDT)",
        min_length=1,
    )

    # Optional format and time range parameters
    file_format: FileFormat = Field(
        default=FileFormat.JPEG, description="Output file format"
    )
    period: ChartPeriod = Field(
        default=ChartPeriod.ONE_YEAR, description="Time period for historical data"
    )
    interval: Optional[ChartInterval] = Field(
        default=None,
        description="Data point interval (automatically determined if not specified)",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date for custom range (overrides period if specified)",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End date for custom range (overrides period if specified)",
    )

    # Chart display options
    max_bars: int = Field(
        default=365, description="Maximum number of bars to display", ge=50, le=1000
    )
    title: Optional[str] = Field(
        default=None, description="Custom chart title (auto-generated if not specified)"
    )
    style_dict: Optional[Dict[str, str]] = Field(
        default=None, description="Custom style dictionary for chart appearance"
    )

    # Technical indicators
    show_volume: bool = Field(default=True, description="Show volume indicator")
    sma_periods: List[int] = Field(
        default_factory=list, description="Simple Moving Average periods", max_length=5
    )
    ema_periods: List[int] = Field(
        default_factory=list, description="Exponential Moving Average periods", max_length=5
    )
    show_rsi: bool = Field(default=False, description="Show Relative Strength Index")
    show_macd: bool = Field(default=False, description="Show MACD indicator")
    show_roc: bool = Field(default=False, description="Show Rate of Change indicator")
    roc_period: int = Field(
        default=12, description="Rate of Change period", ge=1, le=100
    )
    show_vwap: bool = Field(
        default=False, description="Show Volume Weighted Average Price (VWAP)"
    )
    show_bbands: bool = Field(
        default=False, description="Bollinger Bands configuration"
    )
    show_adx: bool = Field(default=False, description="ADX indicator configuration")
    show_mfi: bool = Field(default=False, description="MFI indicator configuration")

    # Y-axis tick density configuration
    use_dynamic_yticks: bool = Field(
        default=True, description="Enable dynamic y-axis tick density"
    )
    max_major_yticks: int = Field(
        default=16, description="Maximum number of major y-axis ticks", ge=2, le=20
    )
    max_minor_per_interval: int = Field(
        default=0, description="Number of minor ticks between major ticks", ge=0, le=5
    )

    # Watermark options
    watermark_text: Optional[str] = Field(
        default_factory=lambda: os.getenv("CHART_WATERMARK_TEXT", "Chapar"),
        description="Watermark text",
    )
    watermark_alpha: float = Field(
        default=0.1, description="Watermark transparency", ge=0.0, le=1.0
    )
    watermark_fontsize: int = Field(
        default=100, description="Watermark font size", ge=10, le=500
    )
    watermark_color: str = Field(default="gray", description="Watermark color")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate and format stock symbol."""
        return v.upper()

    @field_validator("sma_periods", "ema_periods")
    @classmethod
    def validate_ma_periods(cls, v: List[int]) -> List[int]:
        """Validate moving average periods."""
        if v:
            if len(set(v)) != len(v):
                raise ValueError("Duplicate periods are not allowed")
        return sorted(v)

    @model_validator(mode="after")
    def validate_dates(self) -> Any:
        """Validate date range if both dates are provided."""
        start_date = self.start_date
        end_date = self.end_date

        if start_date and end_date and start_date >= end_date:
            raise ValueError("End date must be after start date")

        return self

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "BTCUSDT",
                    "period": "1y",
                    "show_volume": True,
                    "sma_periods": [50, 200],
                    "show_rsi": True,
                }
            ]
        },
    }
