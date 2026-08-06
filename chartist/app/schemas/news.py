from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum
from app.core.json_loader import load_json_file

class NewsMethod(str, Enum):
    SUMMARY_SITES = "summary_sites"
    SUMMARY_SOCIAL = "summary_social"
    SENTIMENT_SITES = "sentiment_sites"
    SENTIMENT_SOCIAL = "sentiment_social"

# Load valid symbols from JSON file
try:
    data = load_json_file("data.json")
    # Valid symbols are now keys in a dictionary
    VALID_SYMBOLS = set(data.get("valid_symbols", {}).keys())
except Exception as e:
    # Fallback to a default set if JSON loading fails
    VALID_SYMBOLS = {'BTC', 'ADA', 'ETH'}
    print(f"Warning: Failed to load symbols from JSON file: {e}")

class NewsRequest(BaseModel):
    symbol: str
    method: NewsMethod
    query: Optional[str] = None  # Optional custom query, if not provided will use default format
    response_language: str = "Persian"

    @field_validator('response_language')
    @classmethod
    def validate_language(cls, value):
        if value not in {"English", "Persian"}:
            raise ValueError("response_language must be English or Persian")
        return value

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, value):
        upper_value = value.upper()  # Convert to uppercase
        if upper_value not in VALID_SYMBOLS:
            raise ValueError(f"Invalid symbol: {upper_value}. Must be one of {VALID_SYMBOLS}.")
        return upper_value
