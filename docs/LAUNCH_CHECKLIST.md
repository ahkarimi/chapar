# Public launch checklist

This checklist turns the repository into a credible public alpha without exaggerating its history or capabilities.

## 1. Create the public repository

- Recommended repository name: `chapar-ai-finance-telegram-bot`.
- Suggested description: `Self-hosted Persian-first market research with FastAPI, Celery, Telegram, and OpenRouter-compatible models.`
- Suggested topics: `python`, `fastapi`, `telegram-bot`, `celery`, `redis`, `postgresql`, `openrouter`, `technical-analysis`, `fintech`, `self-hosted`.
- Upload `docs/images/social-preview.jpg` under the repository's social-preview setting.
- Enable Issues and private vulnerability reporting. Enable Discussions only if you intend to moderate and answer questions there.
- Enable Dependabot alerts/security updates; `.github/dependabot.yml` already configures low-noise monthly version updates.
- Add a private security contact method to the maintainer profile or repository security policy.

## 2. Publish an auditable first release

1. Review the entire staged diff and confirm no private deployment files or copied production data are present.
2. Create the initial commit using a message such as `Initial open-source alpha release`.
3. Push `main`, wait for CI, and protect it from force-pushes after the first green run.
4. Create tag/release `v0.1.0-alpha.1` and summarize the `Unreleased` section of `CHANGELOG.md`.
5. Keep the alpha warning visible. Do not promise API or database compatibility yet.

## 3. Verify from a clean clone

Do not use the maintainer's existing virtual environment as the final proof:

```sh
git clone YOUR_PUBLIC_REPOSITORY_URL
cd chapar-ai-finance-telegram-bot
python -m venv .venv
python -m pip install -r requirements.txt
python -m pytest -q
python -m compileall -q bot chartist
docker compose --env-file .env.example config --quiet
```

Then copy `.env.example` to `.env`, provide private test credentials, and run the complete stack. Verify at least:

- `/health` and authenticated `/docs`;
- one BTC chart request;
- one Telegram command and one conversational message;
- one image-analysis request through the configured multimodal model;
- one Brave-grounded news request and Celery status poll;
- regular versus administrator API-token separation;
- restart behavior with existing PostgreSQL/Redis volumes.

Never commit the credentialed `.env` or the test output if it contains user data.

## 4. Tell the real story

Useful proof already in the repository:

- a real generated chart rather than a design mockup;
- the production architecture and third-party data-flow inventory;
- subscription, referral, broadcast, caching, retry, and background-job workflows shaped by operation;
- CI, container builds, non-root processes, health checks, and security guidance.

If you later publish user counts, latency, uptime, or cost claims, include the measurement period and reproducible method. Until then, say only what is known: the maintainer operated the product for one year before preparing this public alpha.

## 5. Suggested launch post

### English

> I ran a Persian Telegram market-analysis product for one year. Today I am open-sourcing the engineering behind it—not just an LLM demo, but the background jobs, caching, user plans, referrals, admin broadcasts, provider integrations, and deployment work needed to operate it.
>
> Chapar is a self-hosted FastAPI + Celery + Telegram finance bot with OpenRouter-compatible models, grounded Brave news, and generated technical charts. It is an honest alpha: useful today, documented, tested, and still open to improvement.
>
> Repository: YOUR_PUBLIC_REPOSITORY_URL

### فارسی

> بعد از یک سال اجرای واقعی یک محصول تحلیل بازار در تلگرام، کد و تجربه مهندسی پشت آن را متن‌باز می‌کنم؛ نه فقط یک نمونه ساده اتصال به مدل زبانی، بلکه صف پردازش، کش، پلن کاربران، سیستم معرفی، ارسال همگانی، اتصال به سرویس‌های داده و استقرار واقعی.
>
> Chapar یک ربات مالی self-hosted بر پایه FastAPI، Celery و Telegram است که از مدل‌های سازگار با OpenRouter، خبرهای Brave و نمودارهای تکنیکال استفاده می‌کند. پروژه در مرحله آلفاست: قابل استفاده و تست‌شده، اما همچنان آماده مشارکت و بهتر شدن.
>
> مخزن پروژه: YOUR_PUBLIC_REPOSITORY_URL

## 6. First week after launch

- Answer reproducible bug reports quickly, even if the answer is “confirmed; help wanted.”
- Convert two or three small improvements into well-scoped `good first issue` tickets.
- Record a short demo showing Telegram request → background task → chart/analysis result; do not expose tokens or user identities.
- Pin the repository on the maintainer profile and link it from the portfolio/CV.
- Prefer one substantive technical write-up about lessons from the year of operation over repeated generic promotion.
- Track stars, clones, issues, and successful installs as feedback—not as proof of product correctness.
