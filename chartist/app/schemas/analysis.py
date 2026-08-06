from enum import Enum
from pydantic import BaseModel, Field
from app.schemas.chart import ChartRequest


class AnalysisMethod(str, Enum):
    """Supported analysis methods"""

    CRYPTO_TECHNICAL_DH = "crypto_technical_dh"
    CRYPTO_TECHNICAL_H = "crypto_technical_h"
    TECHNICAL = "technical"
    TECHNICAL_WD = "technical_wd"
    TECHNICAL_DH = "technical_dh"


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., BTCUSDT)")
    response_language: str = Field(default="Persian", pattern="^(English|Persian)$")
    analyze_method: AnalysisMethod = Field(
        ...,
        description="Analysis method to apply (e.g., crypto_technical_dh)",
    )
    chart_schema: ChartRequest = Field(
        ..., description="Chart configuration"
    )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "BTCUSDT",
                    "analyze_method": "crypto_technical_dh",
                    "chart_schema": {
                        "symbol": "BTCUSDT",
                        "period": "1y",
                        "show_volume": True,
                    },
                }
            ]
        },
    }
