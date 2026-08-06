# api/v1/referrals.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from app.config import settings
from app.models.database import get_db
from app.models.user import User
from app.core.dependency import get_user_by_telegram
from app.services.toobit_service import ToobitService
from app.schemas.referral import APIResponse, ResponseStatus
from app.core.error_handlers import handle_exception
from app.utils.plan_utils import add_days_to_plan, format_datetime_human, get_remaining_time_human
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/verify", response_model=APIResponse)
async def verify_referral(
    uid_code: str,  # The UID code provided by the user.
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_by_telegram),
    toobit_service: ToobitService = Depends(),
):
    """
    Verify a user's referral by checking if they registered with an allowed invitation code.
    No balance checking required - just need to confirm they used our invite code.
    On success, adds the configured referral reward to the user's plan.
    """

    if user.is_referred:
        return APIResponse(
            status=ResponseStatus.FAILED,
            message="Referral already verified. Plan time has already been granted."
        )

    reward_days = settings.REFERRAL_REWARD_DAYS
    if reward_days is None or reward_days <= 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Referral rewards are not configured.",
        )
    if not toobit_service.allowed_invitation_codes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Referral verification is not configured.",
        )

    try:
        # Convert uid_code to integer for API call
        try:
            uid_int = int(uid_code)
        except ValueError:
            return APIResponse(
                status=ResponseStatus.FAILED,
                message="Invalid UID format. Please provide a valid numeric UID."
            )

        # Use the new simplified verification method
        verification_result = await toobit_service.verify_user_with_invite_code(uid_int)

        if verification_result["verified"]:
            new_end_date = add_days_to_plan(user.plan_end_date, reward_days)

            stmt = (
                update(User)
                .where(User.id == user.id)
                .values(
                    plan_end_date=new_end_date,
                    plan_status="active",
                    plan_updated_at=datetime.now(timezone.utc),
                    is_referred=True,
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"User {user.id} verified with UID {uid_code}, invitation code: {verification_result['invitation_code']}")

            return APIResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Referral verified. {reward_days} days have been added to your plan.",
                data={
                    "days_added": reward_days,
                    "new_plan_end_date": new_end_date.isoformat(),
                    "new_plan_end_date_human": format_datetime_human(new_end_date),
                    "remaining_time_human": get_remaining_time_human(new_end_date),
                    "invitation_code": verification_result["invitation_code"],
                    "uid": uid_code
                }
            )
        else:
            # Verification failed
            error_msg = verification_result.get("error", "Verification failed")
            invitation_code_used = verification_result.get("invitation_code")

            message = "Referral not verified. Please use a configured referral link."

            logger.warning(f"Verification failed for user {user.id}, UID {uid_code}: {error_msg}")

            return APIResponse(
                status=ResponseStatus.PENDING,
                message=message,
                data={
                    "error": error_msg,
                    "invitation_code_used": invitation_code_used,
                }
            )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error verifying referral for user {user.id}, UID {uid_code}: {e}")
        raise handle_exception(e, "verifying referral")
