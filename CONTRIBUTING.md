# Contributing to Chapar

Thanks for helping improve Chapar. This repository contains two Python
applications that share one dependency set:

- `chartist/` is the FastAPI and Celery market-analysis service.
- `bot/` is the Telegram interface and its persistence layer.

## Local checks

Create a virtual environment and install the root requirements as described in
`README.md`. Before opening a change, run:

```sh
make test
python -m compileall -q bot chartist
```

If `make` is unavailable, run `python -m pytest -q` directly. Database integration
tests are skipped by default; point `TEST_DATABASE_URL` at a disposable PostgreSQL
database to include them.

Keep changes focused. Avoid mixing formatting-only changes with behavior changes:
much of the user-facing copy is in Persian, so review depends on small diffs.

## Where bot code belongs

The public entry points are intentionally stable facades. Existing callers should
continue to use `APIRequest`, `PrivateHandler`, and `AdminHandler`.

- `bot/api/request.py`: HTTP session lifecycle and shared request transport.
- `bot/api/*_requests.py`: endpoint methods grouped by API domain.
- `bot/handlers/private_handler.py`: private-chat routing and analysis flow.
- `bot/handlers/message_utils.py`: message formatting and pending-state helpers.
- `bot/handlers/news_workflow.py`: background news jobs and result delivery.
- `bot/handlers/admin_handler.py`: admin command routing.
- `bot/handlers/broadcast.py`: broadcast formatting and delivery.

Place new endpoints and helpers in the narrowest existing module. Add another
mixin only for a genuinely separate workflow; do not expose mixins to callers.

## Change checklist

1. Preserve public imports and method signatures unless an API break is required.
2. Add or update focused tests for behavior changes.
3. Document new settings in `.env.example` and never commit secrets.
4. Run the local checks and describe any check that cannot run locally.
