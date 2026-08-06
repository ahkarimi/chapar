from typing import Optional

from pydantic import BaseModel

class LLMServiceConfig(BaseModel):
    """Configuration for LLM service"""
    api_url: str
    api_key: str
    model: str
    news_model: Optional[str] = None
    response_language: str = "Persian"
    max_tokens: int = 4000
    http_referer: Optional[str] = None
    app_name: Optional[str] = None
