# Telegram bot

The Telegram bot is one component of the Chapar monorepo. Use the root [README](../README.md) for installation and configuration, and [DATABASE.md](DATABASE.md) for persistence notes.

Run it from the repository root so the shared dependency set and `.env` file are used:

```sh
python bot/bot.py
```

The bot requires its Telegram and PostgreSQL settings plus matching `FASTAPI_ACCESS_TOKEN` / `CHARTIST_API_KEY` credentials. Administrative requests use `FASTAPI_ADMIN_ACCESS_TOKEN` / `CHARTIST_ADMIN_API_KEY` when configured.

Database tables are created if missing. This is bootstrap behavior, not a schema-migration system; back up existing data and apply structural changes deliberately.
