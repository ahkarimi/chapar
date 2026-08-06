from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.database import get_db
from app.models.user import User
from app.schemas.user import UserProfile, UserUpdate, UserRegister
from app.utils.plan_utils import add_days_to_plan, get_plan_status, get_remaining_days
from datetime import datetime, timedelta, timezone
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserProfile)
async def register_user(
    user_data: UserRegister,
    telegram_user_id: int = Header(..., alias="TelegramUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new user based on the Telegram user ID.
    If the user already exists, it returns the existing user profile.
    New users get the configured trial plan.
    """
    try:
        # Check if the user exists
        query = select(User).where(User.id == telegram_user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            logger.info(f"User {telegram_user_id} already exists with plan status: {user.plan_status}")
            # Update name and telegram username if they are provided but not set (or have changed)
            updated = False
            if user_data.name and user.name != user_data.name:
                user.name = user_data.name
                updated = True
            if user_data.telegram_username and user.telegram_username != user_data.telegram_username:
                user.telegram_username = user_data.telegram_username
                updated = True
            if updated:
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"Updated user {telegram_user_id} info: name={user.name}, username={user.telegram_username}")
            return user

        trial_duration_hours = settings.TRIAL_DURATION_HOURS
        if trial_duration_hours is None or trial_duration_hours <= 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Trial duration is not configured.",
            )

        trial_end = datetime.now(timezone.utc) + timedelta(hours=trial_duration_hours)

        logger.info(
            "Creating new user %s with a %s-hour trial ending at %s",
            telegram_user_id,
            trial_duration_hours,
            trial_end,
        )

        user = User(
            id=telegram_user_id,
            email=user_data.email,
            phone_number=user_data.phone_number,
            name=user_data.name,
            telegram_username=user_data.telegram_username,
            is_referred=user_data.is_referred,
            total_requests=0,
            plan_end_date=trial_end,
            plan_status="trial",
            plan_updated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Successfully created user {telegram_user_id} with trial ending at {trial_end}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error registering user {telegram_user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}",
        )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    user_data: UserUpdate,
    telegram_user_id: int = Header(..., alias="TelegramUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the user profile based on the Telegram user ID.
    If the user is not found, an error is returned.
    """
    query = select(User).where(User.id == telegram_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Update user fields
    for key, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    try:
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user profile: {str(e)}",
        )


@router.get("/me", response_model=UserProfile)
async def get_profile(
    telegram_user_id: int = Header(..., alias="TelegramUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the current user profile based on the Telegram user ID.
    If the user is not found, an error is returned.
    """
    query = select(User).where(User.id == telegram_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Update plan status if expired
    current_status = get_plan_status(user.plan_end_date, user.plan_status)
    if current_status != user.plan_status:
        user.plan_status = current_status
        await db.commit()
        await db.refresh(user)

    logger.info(f"User {telegram_user_id} profile request: plan_status={user.plan_status}, remaining_days={get_remaining_days(user.plan_end_date)}")

    return user
