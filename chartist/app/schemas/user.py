from pydantic import BaseModel, EmailStr, field_validator, field_serializer
from datetime import datetime
from typing import Optional, Union

from app.utils.plan_utils import get_valid_plan_packages


class UserProfile(BaseModel):
    id: int
    email: Optional[EmailStr]
    phone_number: Optional[str]
    name: Optional[str]
    telegram_username: Optional[str]
    total_requests: int
    is_referred: Optional[bool]
    created_at: datetime
    plan_status: str
    plan_end_date: Optional[datetime]
    remaining_days: int
    remaining_time_human: str
    plan_end_date_human: str

    model_config = {"from_attributes": True}


class UserRegister(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    name: Optional[str] = None
    telegram_username: Optional[str] = None
    is_referred: Optional[bool] = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    name: Optional[str] = None
    telegram_username: Optional[str] = None
    is_referred: Optional[bool] = None


class PlanAddRequest(BaseModel):
    user_id: int
    package_days: int

    @field_validator("package_days")
    @classmethod
    def package_must_be_valid(cls, v):
        valid_packages = get_valid_plan_packages()
        if v not in valid_packages:
            raise ValueError(f"Package days must be one of: {valid_packages}")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
