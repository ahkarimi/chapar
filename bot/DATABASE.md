# Database Management

This project uses SQLAlchemy with PostgreSQL for database operations.

## Automatic Database Setup

The database tables and schema are automatically managed when you run the bot. The system performs the following steps:

1. Uses SQLAlchemy's `create_all()` to create missing tables
2. Adds the nullable per-user language column to existing installations
3. Initializes default settings in the database if needed

This ensures that a new database does not require a separate schema setup command.

## Database Setup (Manual)

If you prefer to set up the database manually before running the bot:

1. Ensure PostgreSQL is running (e.g. in Docker):
   ```
   docker run -d --name postgres -e POSTGRES_PASSWORD=your_password -e POSTGRES_USER=your_user -e POSTGRES_DB=your_db -p 5432:5432 postgres:14
   ```

2. Update your `.env` file with the correct database credentials:
   ```
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB=your_db
   ```

3. Start the bot so it can initialize missing tables:
   ```
   python bot.py
   ```

## Schema Changes

SQLAlchemy's `create_all()` creates missing tables, but it does not rename or remove columns and does not modify existing column types. Back up production data before applying structural changes, then use reviewed SQL appropriate for the deployment.

## Database Models

The main database models are:

1. `UserModel` - Stores user information
   - Located in `database/user.py`
   - Contains user_id, state, toobit_uid, and the selected `en`/`fa` language

2. `SettingsModel` - Stores application settings
   - Located in `database/settings.py`
   - Stores key-value pairs for various application settings

## Database Operations

All database operations should be performed using the SQLAlchemy models and session system, rather than using raw SQL queries. This provides:

1. Type safety
2. SQL injection protection
3. Object-relational mapping
4. Cross-database compatibility

Example of proper database usage:

```python
async with db_connection.get_session() as session:
    # Query
    result = await session.execute(
        select(UserModel).where(UserModel.user_id == user_id)
    )
    user = result.scalars().first()

    # Update
    if user:
        await session.execute(
            update(UserModel)
            .where(UserModel.user_id == user_id)
            .values(state="new_state")
        )
        await session.commit()
```
