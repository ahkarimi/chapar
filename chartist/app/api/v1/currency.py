from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from app.schemas.sourcearena import SourceArenaRequest
from app.providers.sourcearena_provider import SourceArenaProvider
from app.core.dependency import get_user_by_telegram
import logging

# Get logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection for provider
def get_sourcearena_provider() -> SourceArenaProvider:
    return SourceArenaProvider()

@router.post("/")
async def get_currency_data(
    request: SourceArenaRequest,
    provider: SourceArenaProvider = Depends(get_sourcearena_provider),
    user=Depends(get_user_by_telegram),
) -> Dict[str, Any]:
    """
    Get currency data from SourceArena:
    1. Process the request

    Returns:
        Dict[str, Any]: Currency data from SourceArena
    """
    # Step 1: Run the currency data request
    try:
        result = await provider.get_data(request.symbol)
    except Exception as e:
        logger.error(f"Error during currency data request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Currency data request failed. Please try again later.",
        )

    return result
