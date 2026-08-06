import time
import logging
import asyncio
import traceback
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from constants import (
    BOT_TOKEN,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASS,
    POSTGRES_DATABASE,
    API_ENDPOINT,
    ACCESS_TOKEN,
    ADMIN_ACCESS_TOKEN,
    FORCE_JOIN_CHANNEL_ID,
    FORCE_JOIN_CHANNEL_LINK,
    FORCE_JOIN_CHANNEL_TITLE,
    FORCE_JOIN_CHANNEL_2_ID,
    FORCE_JOIN_CHANNEL_2_LINK,
    FORCE_JOIN_CHANNEL_2_TITLE,
)
from api import APIRequest
from database import DatabaseConnection, User, Settings
from handlers import PrivateHandler, AdminHandler
from localization import is_button

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.ERROR,
    force=True,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    await context.application.private_handler.handle_message(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    await context.application.private_handler.handle_message(update, context)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards"""
    await context.application.private_handler.handle_callback_query(update, context)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages"""
    if not update.effective_message:
        return

    # Pass to appropriate handler
    if update.effective_chat.type == "private":
        user_id = update.effective_user.id
        message_text = update.effective_message.text or ""

        # Get user state first - we'll need it for both paths
        user = await context.application.private_handler.user.get_user(user_id)
        user_state = user.get('State', '')

        # For admins
        if context.application.admin_handler and context.application.settings_db.is_admin(user_id):
            # Create a list of admin-specific commands
            admin_commands = [
                '👮 پنل مدیریت',
                '👮 Admin panel',
                '• ارسال پیام همگانی •',
                '• افزودن زمان به کاربر •',
                '• دریافت اطلاعات کاربر •',
                '• تنظیمات •'
            ]

            # List of admin-specific states
            admin_states = [
                'admin', 'settings', 'set_toobit_invitation_link', 'set_toobit_invitation_code',
                'force_join', 'add_force_join', 'admin_force_join_remove_channel',
                'add_admin', 'remove_admin', 'set_help_text', 'set_help_video',
                'set_increase_credit_text', 'set_prize_text',
                'set_dollar_analysis_text', 'set_gold_analysis_text',
                'broadcast_message', 'add_plan_time',
                'add_plan_time_amount', 'get_user_info',
                # broadcast sub-states
                'broadcast_start',
                'broadcast_text',
                'broadcast_media',
                'broadcast_button_text',
                'broadcast_button_link',
                'broadcast_confirm',
            ]

            # Special handling for back button
            if is_button(message_text, "back"):
                # Let the admin handler handle back button in admin states
                if user_state in admin_states:
                    await context.application.admin_handler.handle_admin_message(update, context)
                # Let the private handler handle back button in user states
                else:
                    await context.application.private_handler.handle_message(update, context)
            # Regular admin command or admin state
            elif message_text in admin_commands or user_state in admin_states:
                # Process as admin message
                await context.application.admin_handler.handle_admin_message(update, context)
            # Otherwise treat as a regular user message
            else:
                await context.application.private_handler.handle_message(update, context)
        else:
            # For regular users, always use private_handler
            await context.application.private_handler.handle_message(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    try:
        # Get the exception info
        if context.error:
            error_traceback = "\n".join(
                traceback.format_exception(
                    type(context.error), context.error, context.error.__traceback__
                )
            )

            # Log the full traceback
            logger.error(
                f"Exception while handling update {update.update_id if update else 'None'}:\n{error_traceback}"
            )

            # Log simpler message for common errors
            if hasattr(update, "effective_message") and update.effective_message:
                logger.error(
                    f"Error handling message from {update.effective_user.id if update.effective_user else 'unknown user'}: "
                    f"{str(context.error)[:200]}{'...' if len(str(context.error)) > 200 else ''}"
                )
            else:
                logger.error(f"Error handling update: {str(context.error)[:200]}")
    except Exception as e:
        # Handle errors in the error handler itself
        logger.error(f"Error in error handler: {e}")
        logger.error(f"Original error: {context.error}")
        logger.error(f"Update object: {str(update)[:500]}")


async def initialize_database():
    """Initialize database by creating tables directly without using migrations."""
    try:
        logger.info("Initializing database tables...")
        # Create database connection
        db_connection = DatabaseConnection(
            POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASS, POSTGRES_DATABASE, POSTGRES_PORT
        )
        # Start connection and create tables
        await db_connection.start()
        logger.info("Database tables initialized successfully")
        return db_connection
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e


async def start_bot():
    """Initialize and start the bot"""
    required_settings = {
        "BOT_TOKEN": BOT_TOKEN,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASS,
        "POSTGRES_TELEGRAM_DB": POSTGRES_DATABASE,
        "FASTAPI_ENDPOINT": API_ENDPOINT,
        "FASTAPI_ACCESS_TOKEN": ACCESS_TOKEN,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")

    # Initialize database
    db_connection = await initialize_database()

    # Initialize bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Get bot info
    bot_info = await application.bot.get_me()
    bot_username = bot_info.username
    start_time = int(time.time())

    # Initialize API client
    api_client = APIRequest(
        API_ENDPOINT,
        ACCESS_TOKEN,
        admin_access_token=ADMIN_ACCESS_TOKEN,
    )

    # Initialize database models
    settings_db = Settings(db_connection)
    await settings_db.load_settings()

    # Initialize force join channels list
    force_join_channels = []

    # Add first channel if configured
    if FORCE_JOIN_CHANNEL_ID:
        force_join_channels.append({
            "channel_id": FORCE_JOIN_CHANNEL_ID,
            "join_link": FORCE_JOIN_CHANNEL_LINK,
            "title": FORCE_JOIN_CHANNEL_TITLE
        })

    # Add second channel if configured
    if FORCE_JOIN_CHANNEL_2_ID:
        force_join_channels.append({
            "channel_id": FORCE_JOIN_CHANNEL_2_ID,
            "join_link": FORCE_JOIN_CHANNEL_2_LINK,
            "title": FORCE_JOIN_CHANNEL_2_TITLE
        })

    settings_db.force_join_channels = force_join_channels

    user_db = User(db_connection, api_client)

    # Initialize handlers
    private_handler = PrivateHandler(user_db, settings_db, api_client)
    admin_handler = AdminHandler(user_db, settings_db, api_client)

    # Set bot info in handlers
    private_handler.set_bot_info(bot_username, start_time)
    admin_handler.set_start_time(start_time)

    # Store handlers in application for context access
    application.private_handler = private_handler
    application.admin_handler = admin_handler
    application.settings_db = settings_db

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Register message handler (for both private and admin, including media)
    application.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
            message_handler,
        )
    )

    # Register error handler
    application.add_error_handler(error_handler)

    # Send startup notification
    await private_handler.send_message_to_admins("Bot was started...", application.bot)
    logger.info("Bot initialization completed")

    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Keep the bot running until interrupted
    try:
        await asyncio.Future()  # Run forever until cancelled
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot was stopped by user")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    # Run the bot in the asyncio event loop
    try:
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        logger.info("Bot has been stopped")
