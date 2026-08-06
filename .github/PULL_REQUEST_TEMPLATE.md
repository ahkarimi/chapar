## What changed

Describe the user-visible problem and the focused solution.

## How it was tested

- [ ] `python -m pytest -q`
- [ ] `python -m compileall -q bot chartist`
- [ ] `docker compose --env-file .env.example config --quiet`
- [ ] Added or updated focused tests where behavior changed

## Safety and scope

- [ ] No credentials, `.env` files, personal data, or production logs are included
- [ ] New settings are documented in `.env.example`
- [ ] Public imports and API compatibility are preserved or the break is documented
- [ ] Unrelated formatting/refactoring is excluded
