from sqlalchemy import Column, Integer, String, Text, select, update, insert, BigInteger
from sqlalchemy.ext.asyncio import AsyncSession
from .connection import Base
import logging
import asyncio

logger = logging.getLogger(__name__)

class UserModel(Base):
    """SQLAlchemy model for users table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(BigInteger, unique=True, nullable=False)
    state = Column(String(255), nullable=True)
    toobit_uid = Column(String(255), unique=True, nullable=True)
    language = Column(String(2), nullable=True)


class User:
    """User database operations class using SQLAlchemy."""

    def __init__(self, connection, api_request):
        """Initialize with database connection and API request handler.

        Args:
            connection: Database connection object
            api_request: API request handler
        """
        self.database = connection
        self.request = api_request

    async def get_user(self, user_id):
        """Get a user from the database or create if not exists.

        Args:
            user_id (int): Telegram user ID

        Returns:
            dict: User information
        """
        async with self.database.get_session() as session:
            # Check if user exists
            result = await session.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            user = result.scalars().first()

            if not user:
                # Create user if not exists
                await self.add_user(user_id)
                # Fetch the newly created user
                return await self.get_user(user_id)

            # Return user data as dict
            return {
                "id": user.id,
                "UserId": user.user_id,
                "State": user.state,
                "ToobitUID": user.toobit_uid,
                "Language": user.language,
            }

    async def add_user(self, user_id):
        """Add a new user to the database.

        Args:
            user_id (int): Telegram user ID
        """
        # First try to register with API, with limited retry mechanism
        max_retries = 1  # Reduced from 3 to 1 to avoid excessive retries
        retry_count = 0
        api_success = False

        while retry_count < max_retries and not api_success:
            try:
                # Notify API service
                api_response = await self.request.add_user(user_id)
                if api_response:
                    api_success = True
                    logger.info(f"Successfully registered user {user_id} with API")
                else:
                    logger.warning(f"API returned empty response for user {user_id}")
            except Exception as e:
                retry_count += 1
                logger.warning(f"Failed to notify API about new user {user_id} (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # Wait before retrying

        if not api_success:
            logger.error(f"Failed to register user {user_id} with API after {max_retries} attempts - continuing with local registration only")

        # Continue with local database registration regardless of API result
        async with self.database.get_session() as session:
            async with session.begin():  # This creates a transaction
                try:
                    # Check if user already exists
                    result = await session.execute(
                        select(UserModel).where(UserModel.user_id == user_id)
                    )
                    existing_user = result.scalars().first()

                    if not existing_user:
                        # Create new user with proper ORM approach
                        user = UserModel()
                        user.user_id = user_id
                        user.state = None
                        user.toobit_uid = None
                        user.language = None
                        session.add(user)
                        # The actual commit happens automatically at the end of the session.begin() block
                        logger.info(f"Added new user to database: {user_id}")
                except Exception as e:
                    # Transaction will be automatically rolled back on exception
                    logger.error(f"Error adding user {user_id} to database: {e}")

    async def set_state(self, user_id, state):
        """Set user state in the database.

        Args:
            user_id (int): Telegram user ID
            state (str): State to set
        """
        async with self.database.get_session() as session:
            try:
                # Update user state
                await session.execute(
                    update(UserModel)
                    .where(UserModel.user_id == user_id)
                    .values(state=state)
                )
                await session.commit()
                logger.debug(f"Set state for user {user_id}: {state}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error setting state for user {user_id}: {e}")

    async def set_language(self, user_id, language):
        """Persist a user's UI and analysis language."""
        if language not in {"en", "fa"}:
            raise ValueError("language must be 'en' or 'fa'")
        async with self.database.get_session() as session:
            try:
                await session.execute(
                    update(UserModel)
                    .where(UserModel.user_id == user_id)
                    .values(language=language, state="")
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Error setting language for user %s", user_id)
                raise

    async def toobit_uid_exists(self, uid):
        """Check if a Toobit UID already exists in the database.

        Args:
            uid (str): Toobit UID to check

        Returns:
            bool: True if exists, False otherwise
        """
        async with self.database.get_session() as session:
            try:
                result = await session.execute(
                    select(UserModel).where(UserModel.toobit_uid == uid)
                )
                user = result.scalars().first()
                return user is not None
            except Exception as e:
                logger.error(f"Error checking if Toobit UID exists {uid}: {e}")
                # In case of error, we should return False to allow retry
                return False
            finally:
                # Ensure session is properly closed
                await session.close()

    async def set_toobit_uid(self, user_id, uid):
        """Set a user's Toobit UID.

        Args:
            user_id (int): Telegram user ID
            uid (str): Toobit UID to set
        """
        async with self.database.get_session() as session:
            try:
                await session.execute(
                    update(UserModel)
                    .where(UserModel.user_id == user_id)
                    .values(toobit_uid=uid)
                )
                await session.commit()
                logger.debug(f"Set Toobit UID for user {user_id}: {uid}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error setting Toobit UID for user {user_id}: {e}")

    async def get_all_users(self):
        """Get all users from the database.

        Returns:
            list: List of user dictionaries
        """
        async with self.database.get_session() as session:
            try:
                result = await session.execute(select(UserModel))
                users = result.scalars().all()

                return [
                    {
                        "id": user.id,
                        "user_id": user.user_id,
                        "state": user.state,
                        "toobit_uid": user.toobit_uid,
                        "language": user.language,
                    }
                    for user in users
                ]
            except Exception as e:
                logger.error(f"Error getting all users: {e}")
                return []
