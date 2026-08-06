from enum import Enum
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')  # Generic type for response data

class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    ERROR = "error"

class APIResponse(BaseModel, Generic[T]):
    """Standard API response format for all endpoints"""
    status: ResponseStatus
    message: str
    data: Optional[T] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "Operation completed successfully",
                    "data": {"sample": "data"},
                    "metadata": {"processing_time": "0.5s"}
                }
            ]
        }
    }
