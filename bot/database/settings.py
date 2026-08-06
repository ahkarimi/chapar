import json
from sqlalchemy import Column, Integer, String, Text, select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from .connection import Base
from constants import ADMINS


class SettingsModel(Base):
    """SQLAlchemy model for settings table."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)


class Settings:
    """Settings database operations class using SQLAlchemy."""

    def __init__(self, connection):
        """Initialize with database connection.

        Args:
            connection: Database connection object
        """
        self.database = connection
        # Settings will be loaded asynchronously
        self.force_join_channels = []
        self.admins = []
        self.toobit_invitation_code = ""
        self.toobit_invitation_link = ""
        self.help_text = ""
        self.help_video = ""
        self.increase_credit_text = ""
        self.prize_text = ""
        self.gold_analysis_text = ""
        self.dollar_analysis_text = ""

    async def load_settings(self):
        """Load all settings from database."""
        await self.init_keys()
        # Load settings from database
        self.force_join_channels = json.loads(await self.get("force_join_channels") or "[]")
        self.admins = json.loads(await self.get("admins") or "[]")
        self.toobit_invitation_code = await self.get("toobit_invitation_code") or ""
        self.toobit_invitation_link = await self.get("toobit_invitation_link") or ""
        self.help_text = await self.get("help_text") or ""
        self.help_video = await self.get("help_video") or ""
        self.increase_credit_text = await self.get("increase_credit_text") or ""
        self.prize_text = await self.get("prize_text") or ""
        self.gold_analysis_text = await self.get("gold_analysis_text") or ""
        self.dollar_analysis_text = await self.get("dollar_analysis_text") or ""

    async def init_keys(self):
        """Initialize settings keys in the database if they don't exist."""
        # List of default settings
        default_settings = {
            "force_join_channels": "[]",
            "admins": "[]",
            "toobit_invitation_code": "",
            "toobit_invitation_link": "",
            "help_text": "",
            "help_video": "",
            "increase_credit_text": "",
            "prize_text": "",
            "gold_analysis_text": "",
            "dollar_analysis_text": "",
        }

        async with self.database.get_session() as session:
            # Check each key and insert if it doesn't exist
            for key, value in default_settings.items():
                # Check if setting exists
                result = await session.execute(
                    select(SettingsModel).where(SettingsModel.key == key)
                )
                existing_setting = result.scalars().first()

                if not existing_setting:
                    # Create new setting
                    new_setting = SettingsModel(key=key, value=value)
                    session.add(new_setting)

            # Commit all changes
            await session.commit()

    async def get(self, key):
        """Get a setting value by key.

        Args:
            key (str): Setting key

        Returns:
            str: Setting value or None if not found
        """
        async with self.database.get_session() as session:
            result = await session.execute(
                select(SettingsModel).where(SettingsModel.key == key)
            )
            setting = result.scalars().first()

            return setting.value if setting else None

    async def set(self, key, value):
        """Set a setting value.

        Args:
            key (str): Setting key
            value (str): Setting value
        """
        async with self.database.get_session() as session:
            try:
                # Check if setting exists
                result = await session.execute(
                    select(SettingsModel).where(SettingsModel.key == key)
                )
                setting = result.scalars().first()

                if setting:
                    # Update existing setting
                    await session.execute(
                        update(SettingsModel)
                        .where(SettingsModel.key == key)
                        .values(value=value)
                    )
                else:
                    # Create new setting
                    new_setting = SettingsModel(key=key, value=value)
                    session.add(new_setting)

                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Error setting value: {e}")

    async def add_force_join(self, channel_id, join_link):
        """Add a force join channel.

        Args:
            channel_id (int): Channel ID
            join_link (str): Channel join link
        """
        # Add to the list
        self.force_join_channels.append(
            {"channel_id": channel_id, "join_link": join_link}
        )
        # Save to database
        await self.set("force_join_channels", json.dumps(self.force_join_channels))

    async def remove_force_join(self, channel_id):
        """Remove a force join channel.

        Args:
            channel_id (int): Channel ID to remove
        """
        self.force_join_channels = [
            channel
            for channel in self.force_join_channels
            if channel["channel_id"] != channel_id
        ]
        await self.set("force_join_channels", json.dumps(self.force_join_channels))

    async def clear_force_joins(self):
        """Clear all force join channels."""
        await self.set("force_join_channels", "[]")
        self.force_join_channels = []

    def get_force_joins(self):
        """Get all force join channels.

        Returns:
            list: Force join channels
        """
        return self.force_join_channels

    def get_force_join_ids(self):
        """Get IDs of all force join channels.

        Returns:
            list: Channel IDs
        """
        return [channel["channel_id"] for channel in self.force_join_channels]

    def get_admins(self):
        """Get all admin user IDs.

        Returns:
            list: Admin user IDs
        """
        # Combine database admins with config admins
        return self.admins + ADMINS

    def is_admin(self, user_id):
        """Check if a user is an admin.

        Args:
            user_id (int): User ID to check

        Returns:
            bool: True if admin, False otherwise
        """
        # Convert user_id to string for comparison
        user_id_str = str(user_id)
        return user_id_str in self.get_admins() or user_id in self.get_admins()

    def is_full_admin(self, user_id):
        """Check if a user is a full admin (from config).

        Args:
            user_id (int): User ID to check

        Returns:
            bool: True if full admin, False otherwise
        """
        # Convert user_id to string for comparison
        user_id_str = str(user_id)
        return user_id_str in ADMINS or user_id in ADMINS

    async def add_admin(self, user_id):
        """Add a user as admin.

        Args:
            user_id (int): User ID to add
        """
        if user_id not in self.admins:
            self.admins.append(user_id)
            await self.set("admins", json.dumps(self.admins))

    async def remove_admin(self, user_id):
        """Remove a user from admins.

        Args:
            user_id (int): User ID to remove
        """
        if user_id in self.admins:
            self.admins.remove(user_id)
            await self.set("admins", json.dumps(self.admins))

    def get_toobit_invitation_code(self):
        """Get Toobit invitation code.

        Returns:
            str: Invitation code
        """
        return self.toobit_invitation_code

    def set_toobit_invitation_code(self, code):
        """Set Toobit invitation code.

        Args:
            code (str): Invitation code
        """
        return self._update_setting("toobit_invitation_code", code)

    def get_toobit_invitation_link(self):
        """Get Toobit invitation link.

        Returns:
            str: Invitation link
        """
        return self.toobit_invitation_link

    def set_toobit_invitation_link(self, link):
        """Set Toobit invitation link.

        Args:
            link (str): Invitation link
        """
        return self._update_setting("toobit_invitation_link", link)

    def get_help_text(self):
        """Get help text.

        Returns:
            str: Help text
        """
        return self.help_text

    def set_help_text(self, text):
        """Set help text.

        Args:
            text (str): Help text
        """
        return self._update_setting("help_text", text)

    def get_help_video(self):
        """Get help video.

        Returns:
            str: Help video
        """
        return "BAACAgQAAxkBAAEDBb1qNYxbG2rN0lf_3VwZ_kcrzE9dpAACjB8AAh1iqFEiDNy1c0WLnzwE"

    def set_help_video(self, video):
        """Set help video.

        Args:
            video (str): Help video
        """
        return self._update_setting("help_video", video)

    def get_increase_credit_text(self):
        """Get increase credit text.

        Returns:
            str: Increase credit text
        """
        return self.increase_credit_text

    def set_increase_credit_text(self, text):
        """Set increase credit text.

        Args:
            text (str): Increase credit text
        """
        return self._update_setting("increase_credit_text", text)

    def get_prize_text(self):
        """Get prize text.

        Returns:
            str: Prize text
        """
        return self.prize_text

    def set_prize_text(self, text):
        """Set prize text.

        Args:
            text (str): Prize text
        """
        return self._update_setting("prize_text", text)

    def get_gold_analysis_text(self):
        """Get gold analysis text.

        Returns:
            str: Gold analysis text
        """
        return self.gold_analysis_text

    def set_gold_analysis_text(self, text):
        """Set gold analysis text.

        Args:
            text (str): Gold analysis text
        """
        return self._update_setting("gold_analysis_text", text)

    def get_dollar_analysis_text(self):
        """Get dollar analysis text.

        Returns:
            str: Dollar analysis text
        """
        return self.dollar_analysis_text

    def set_dollar_analysis_text(self, text):
        """Set dollar analysis text.

        Args:
            text (str): Dollar analysis text
        """
        return self._update_setting("dollar_analysis_text", text)

    async def _update_setting(self, key, value):
        """Update a setting and cache it.

        Args:
            key (str): Setting key
            value (str): Setting value

        Returns:
            Coroutine: Set operation
        """
        # Update local cache
        setattr(self, key, value)
        # Save to database
        return await self.set(key, value)
