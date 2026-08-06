from pydantic import BaseModel
from typing import Optional

class SourceArenaRequest(BaseModel):
    """
    Schema for SourceArena currency data requests.

    Attributes:
        symbol (Optional[str]): Optional currency symbol/slug to retrieve data for.
                               If not provided, returns data for all currencies.
    """
    symbol: Optional[str] = None
