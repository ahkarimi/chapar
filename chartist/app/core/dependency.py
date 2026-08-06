from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.user import User

async def get_user_by_telegram(
    telegram_user_id: int = Header(..., alias="TelegramUID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Retrieve the User based on the Telegram user ID provided in the header.
    """
    query = select(User).where(User.id == telegram_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first."
        )
    return user
