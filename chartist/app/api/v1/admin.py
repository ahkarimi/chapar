from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import extract, func, and_, select, delete
from app.schemas.user import PlanAddRequest, UserProfile
from app.schemas.admin import AdminReportsResponse, MonthlyAnalysisReport, MonthlyPlanSubscriptionReport, WeeklyAnalysisReport, NewUsersReport, PlanStatusReport
from app.models.user import User
from app.models.database import get_db
from app.models.history import PlanHistory, AnalysisHistory, NotificationLog
from app.utils.plan_utils import (
    add_days_to_plan, get_plan_status, get_remaining_days, get_valid_plan_packages, is_valid_package, has_active_plan,
    format_datetime_human, get_remaining_time_human
)
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plan/add")
async def add_plan_time(
    update: PlanAddRequest, db: AsyncSession = Depends(get_db)
):
    """Add time to a user's plan."""
    logger.info(f"=== ADMIN PLAN ADD ===")
    logger.info(f"User ID: {update.user_id}")
    logger.info(f"Package days: {update.package_days}")

    # Validate package
    if not is_valid_package(update.package_days):
        valid_packages = get_valid_plan_packages()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid package. Configured packages: {valid_packages}"
        )

    # Start by getting the user
    user = await db.get(User, update.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Log user's current state
    current_end = user.plan_end_date
    logger.info(f"User's current plan end date: {current_end}")

    # Calculate new plan end date
    new_end_date = add_days_to_plan(current_end, update.package_days)
    logger.info(f"New plan end date: {new_end_date}")

    # Update user plan
    user.plan_end_date = new_end_date
    user.plan_status = get_plan_status(new_end_date, "active")
    user.plan_updated_at = datetime.now(timezone.utc)

    # Reset plan-expiry notifications so the user gets re-notified
    # at 75% / 85% / expired of the freshly extended period.
    await db.execute(
        delete(NotificationLog).where(NotificationLog.user_id == update.user_id)
    )

    # Create and add a plan history entry
    history_entry = PlanHistory(
        user_id=update.user_id,
        days_added=update.package_days,
        plan_end_date_after=new_end_date
    )
    db.add(history_entry)

    # Explicitly commit the changes
    await db.commit()
    await db.refresh(user)

    logger.info(
        f"Admin added {update.package_days} days to user {update.user_id}. New end date: {new_end_date}"
    )

    return {
        "message": "Plan time added successfully",
        "days_added": update.package_days,
        "new_plan_end_date": new_end_date.isoformat(),
        "new_plan_end_date_human": format_datetime_human(new_end_date),
        "remaining_days": get_remaining_days(new_end_date),
        "remaining_time_human": get_remaining_time_human(new_end_date),
        "plan_status": user.plan_status
    }


@router.get("/reports", response_model=AdminReportsResponse)
async def get_admin_reports(db: AsyncSession = Depends(get_db)):
    """Get comprehensive admin reports including monthly analysis data and plan subscriptions."""

    # 1. Monthly Analysis Reports
    month_expr = func.to_char(AnalysisHistory.created_at, 'YYYY-MM')
    monthly_analysis_query = await db.execute(
        select(
            month_expr.label('month'),
            func.count(AnalysisHistory.id).label('total_analyses')
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )

    monthly_analyses = []
    for row in monthly_analysis_query.fetchall():
        monthly_analyses.append(MonthlyAnalysisReport(
            month=row.month,
            total_analyses=row.total_analyses
        ))

    # 2. Monthly Plan Subscriptions (grouped by package days)
    month_plan_expr = func.to_char(PlanHistory.created_at, 'YYYY-MM')
    monthly_plan_query = await db.execute(
        select(
            month_plan_expr.label('month'),
            PlanHistory.days_added.label('package_days'),
            func.count(PlanHistory.id).label('total_subscriptions')
        )
        .group_by(month_plan_expr, PlanHistory.days_added)
        .order_by(month_plan_expr, PlanHistory.days_added)
    )

    monthly_plan_subscriptions = []
    for row in monthly_plan_query.fetchall():
        monthly_plan_subscriptions.append(MonthlyPlanSubscriptionReport(
            month=row.month,
            package_days=row.package_days,
            total_subscriptions=row.total_subscriptions
        ))

    # 3. Weekly Analysis (Last 7 days)
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_analysis_query = await db.execute(
        select(func.count(AnalysisHistory.id))
        .where(AnalysisHistory.created_at >= one_week_ago)
    )
    weekly_analysis_count = weekly_analysis_query.scalar() or 0

    weekly_analysis = WeeklyAnalysisReport(
        total_analyses=weekly_analysis_count
    )

    # 4. New Users (Last hour and last day)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

    # Users in last hour
    last_hour_users_query = await db.execute(
        select(func.count(User.id))
        .where(User.created_at >= one_hour_ago)
    )
    last_hour_users = last_hour_users_query.scalar() or 0

    # Users in last day
    last_day_users_query = await db.execute(
        select(func.count(User.id))
        .where(User.created_at >= one_day_ago)
    )
    last_day_users = last_day_users_query.scalar() or 0

    new_users = NewUsersReport(
        last_hour=last_hour_users,
        last_day=last_day_users
    )

    # 5. Plan Status Report
    now = datetime.now(timezone.utc)

    active_users_query = await db.execute(
        select(func.count(User.id))
        .where(User.plan_end_date > now)
    )
    active_users = active_users_query.scalar() or 0

    expired_users_query = await db.execute(
        select(func.count(User.id))
        .where(
            and_(
                User.plan_end_date <= now,
                User.plan_end_date.isnot(None)
            )
        )
    )
    expired_users = expired_users_query.scalar() or 0

    trial_users_query = await db.execute(
        select(func.count(User.id))
        .where(User.plan_status == "trial")
    )
    trial_users = trial_users_query.scalar() or 0

    plan_status = PlanStatusReport(
        active_users=active_users,
        expired_users=expired_users,
        trial_users=trial_users
    )

    return AdminReportsResponse(
        monthly_analyses=monthly_analyses,
        monthly_plan_subscriptions=monthly_plan_subscriptions,
        weekly_analysis=weekly_analysis,
        new_users=new_users,
        plan_status=plan_status
    )


@router.get("/users/search", response_model=UserProfile)
async def search_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Search for a user by telegram username (case-insensitive)."""
    query = select(User).where(func.lower(User.telegram_username) == username.lower())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this username"
        )

    # Update plan status if expired
    current_status = get_plan_status(user.plan_end_date, user.plan_status)
    if current_status != user.plan_status:
        user.plan_status = current_status
        await db.commit()
        await db.refresh(user)

    return user


@router.get("/plan/debug/{user_id}")
async def debug_user_plan(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to show detailed plan information for a user"""
    try:
        # Get user from database
        user = await db.get(User, user_id)
        if not user:
            return {"error": "User not found"}

        # Get recent plan history
        history_query = await db.execute(
            select(PlanHistory)
            .where(PlanHistory.user_id == user_id)
            .order_by(PlanHistory.created_at.desc())
            .limit(5)
        )
        recent_history = history_query.scalars().all()

        return {
            "user_id": user_id,
            "database_info": {
                "plan_end_date": user.plan_end_date.isoformat() if user.plan_end_date else None,
                "plan_end_date_human": format_datetime_human(user.plan_end_date),
                "plan_status": user.plan_status,
                "total_requests": user.total_requests,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "created_at_human": format_datetime_human(user.created_at)
            },
            "plan_info": {
                "is_active": has_active_plan(user.plan_end_date),
                "remaining_days": get_remaining_days(user.plan_end_date),
                "remaining_time_human": get_remaining_time_human(user.plan_end_date),
                "current_status": get_plan_status(user.plan_end_date, user.plan_status)
            },
            "recent_plan_history": [
                {
                    "days_added": h.days_added,
                    "plan_end_date_after": h.plan_end_date_after.isoformat() if h.plan_end_date_after else None,
                    "plan_end_date_after_human": format_datetime_human(h.plan_end_date_after),
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                    "created_at_human": format_datetime_human(h.created_at)
                }
                for h in recent_history
            ]
        }

    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {"error": str(e)}


@router.get("/plan/history/{user_id}")
async def get_user_plan_history(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get complete plan history for a user."""
    try:
        # Get user from database
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get all plan history ordered by date descending
        history_query = await db.execute(
            select(PlanHistory)
            .where(PlanHistory.user_id == user_id)
            .order_by(PlanHistory.created_at.desc())
        )
        history = history_query.scalars().all()

        # Build summary
        total_purchases = len(history)
        unique_plans = sorted(set(h.days_added for h in history))

        return {
            "user_id": user_id,
            "total_purchases": total_purchases,
            "unique_plans": unique_plans,
            "history": [
                {
                    "days_added": h.days_added,
                    "plan_end_date_after_human": format_datetime_human(h.plan_end_date_after),
                    "created_at_human": format_datetime_human(h.created_at)
                }
                for h in history
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan history for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting plan history: {str(e)}"
        )
