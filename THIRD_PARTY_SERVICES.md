# Third-party services and data flow

Chapar is self-hosted, but several features call external services. Operators should understand these boundaries before enabling the bot for other users. This document describes what the current code sends; it is not a substitute for reviewing each provider's current terms and privacy policy.

## External services

| Service | Used for | Data sent by this project | Configuration | Can be disabled? |
| --- | --- | --- | --- | --- |
| Telegram Bot API | Receiving commands and delivering charts, analysis, news, and broadcasts | Telegram chat/user identifiers, message content, generated files, and bot responses | `BOT_TOKEN` and channel settings | No, not when running the Telegram interface; the FastAPI service can run separately |
| OpenAI-compatible LLM endpoint (OpenRouter by default) | Chat, chart-image analysis, and news synthesis | User chat text and bounded history; generated chart images and requested symbol/method; or Brave result titles, descriptions, URLs, and dates | `LLM_BASE_URL`, `LLM_API_KEY`, and the `LLM_*_MODEL` settings | Yes; chart generation and non-LLM API features remain available |
| Brave News Search | Retrieving current news before grounded summarization | Search query, symbol, method, result count, and freshness parameters; no Telegram identifier is intentionally included | `BRAVE_SEARCH_API_KEY` | Yes; only grounded news is affected |
| Toobit public market API | Crypto candle data used to render charts | Symbol, interval, time range, and result limit | No credential is required for public candles | No for the current default crypto chart provider |
| Toobit authenticated API | Optional referral/invitation verification | Configured API key plus signed query parameters; a submitted exchange UID may be included | `TOOBIT_API_KEY`, `TOOBIT_SECRET_KEY`, and referral settings | Yes; disable the exchange-verification workflow |
| SourceArena | Persian-market and currency data | Requested symbol/currency query and the configured provider token | `SOURCEARENA_TOKEN` | Yes if those markets/currency endpoints are not used |
| CoinGecko | Trending coin suggestions in the bot | A request to the public trending endpoint; no user identifier is intentionally included | No key in the current implementation | Yes; only trending suggestions are affected |

| Binance public market API | Crypto candle data used to render charts (free public API option/fallback) | Symbol, interval, time range, and result limit | No credential required | Yes; configurable via `CRYPTO_DATA_PROVIDER` / `FALLBACK_CRYPTO_PROVIDER` |
| Yahoo Finance API | Public stock and crypto market candle data (free public API option/fallback) | Symbol, period, and interval query parameters | No credential required | Yes; configurable via `STOCK_DATA_PROVIDER` / `FALLBACK_STOCK_PROVIDER` |

The chart-service uses an Abstract Data Provider Interface (`BaseExchangeProvider`) with dynamic provider selection and automatic fallback:
- `CRYPTO_DATA_PROVIDER` (default `toobit`, alternative `binance` or `yahoo`)
- `FALLBACK_CRYPTO_PROVIDER` (default `binance`)
- `STOCK_DATA_PROVIDER` (default `sourcearena`, alternative `yahoo`)
- `FALLBACK_STOCK_PROVIDER` (default `yahoo`)

## Locally operated data stores

- PostgreSQL stores Telegram user identifiers, plan/referral state, settings, and analysis history.
- Redis stores caches, Celery broker/result data, rate-limit state, and recent LLM conversation history. Chat history is currently written with a seven-day expiration and is bounded by `LLM_MAX_HISTORY_MESSAGES`.
- Application logs can contain identifiers, symbols, task IDs, provider errors, and operational metadata. Request bodies and credentials should not be logged.

PostgreSQL and Redis are third-party software but remain inside the operator-controlled Docker network in the supplied Compose deployment.

## Operator checklist

1. Enable only the integrations your deployment needs and leave unused credentials blank.
2. Tell users that their messages or generated charts may be sent to the configured LLM provider.
3. Review provider retention, training, regional-transfer, and content policies independently.
4. Do not place secrets in model prompts, issue reports, screenshots, or logs.
5. Use a dedicated service account and least-privilege credentials where providers support them.
6. Set retention and deletion expectations for PostgreSQL backups, Redis persistence, and logs.
7. Treat provider responses as untrusted data. News content can contain prompt-injection text even though the LLM prompt explicitly labels results as data rather than instructions.

Changing `LLM_BASE_URL` changes the organization receiving LLM requests. Operators are responsible for verifying that their chosen OpenAI-compatible endpoint supports the selected models and multimodal payloads.
