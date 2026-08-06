from fastapi import HTTPException, status
from app.schemas.referral import APIResponse, ResponseStatus
import logging

logger = logging.getLogger(__name__)

def handle_exception(e: Exception, operation_name: str) -> HTTPException:
    """
    Standardized exception handler that logs the error and returns an appropriate HTTPException.

    Args:
        e: The exception that was raised
        operation_name: A description of the operation that failed

    Returns:
        HTTPException: A properly formatted HTTP exception
    """
    error_msg = f"Error during {operation_name}: {str(e)}"
    logger.error(error_msg)

    # Determine if this is a client error or server error
    if isinstance(e, ValueError) or isinstance(e, KeyError):
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Create a standardized error response
    error_response = APIResponse(
        status=ResponseStatus.ERROR,
        message=f"Failed to {operation_name}. {str(e) if status_code == status.HTTP_400_BAD_REQUEST else 'An unexpected error occurred.'}"
    )

    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump()
    )
