# Configuration — Fixzy Marketing Tools

All configuration comes from environment variables (loaded from `.env` in the
repo root — copy `.env.example` and edit). Nothing is hardcoded. Restart the
app after editing.

## Core

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | ephemeral (warns) | Flask session/CSRF signing key. Generate: `openssl rand -hex 32`. Unset = sessions break on every restart. |
| `ADMIN_USER` | No | `admin` | HTTP Basic username for the whole UI. |
| `ADMIN_PASSWORD` | **Yes for any non-LAN use** | empty | If empty the UI only answers LAN clients and refuses everything else (fail-closed). Set it before exposing the app. |
| `DATABASE_URL` | No | `sqlite:///fixzy.db` | SQLAlchemy URL. Docker compose overrides to `sqlite:////data/fixzy.db` (named volume). |
| `APP_PORT` | No | `5558` | Host port published by `docker-compose.yml` (container port is always 5558). |
| `PUBLIC_BASE_URL` | Yes in production | `http://localhost:5558` | Base URL used in unsubscribe links sent to recipients — must be publicly reachable. |

## Email — Brevo SMTP relay

| Variable | Required | Default | Description |
|---|---|---|---|
| `BREVO_SMTP_HOST` | No | `smtp-relay.brevo.com` | SMTP host. |
| `BREVO_SMTP_PORT` | No | `587` | SMTP port (STARTTLS). |
| `BREVO_SMTP_USER` | For email | — | SMTP login email from Brevo dashboard. |
| `BREVO_SMTP_KEY` | For email | — | SMTP key (`xsmtpsib-…`). |
| `MAIL_FROM` | For email | — | From header, e.g. `Fixzy <hello@fixzy.my>`. |
| `BREVO_WEBHOOK_SECRET` | For tracking | — | Shared secret for `POST /webhooks/brevo?key=<secret>` (open/bounce events). Register the webhook in Brevo with this key. |

## Telegram

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | For Telegram | — | From @BotFather. |
| `TELEGRAM_WEBHOOK_SECRET` | Recommended | — | Registered as the webhook `secret_token`; when set, updates without a matching `X-Telegram-Bot-Api-Secret-Token` header are rejected (fail-closed). |

## SMS

| Variable | Required | Default | Description |
|---|---|---|---|
| `TWILIO_ACCOUNT_SID` | For Twilio | — | Twilio account SID. |
| `TWILIO_AUTH_TOKEN` | For Twilio | — | Twilio auth token. |
| `TWILIO_FROM_NUMBER` | For Twilio | — | e.g. `+60123456789`. |
| `REDSMS_USERNAME` / `REDSMS_PASSWORD` | For RedSMS | — | RedSMS MY fallback (verify API format against your account docs). |
| `REDSMS_SENDER_ID` | No | `Fixzy` | RedSMS sender ID. |

## WhatsApp / Messenger / Instagram (Meta)

| Variable | Required | Default | Description |
|---|---|---|---|
| `WHATSAPP_ACCESS_TOKEN` | For WhatsApp | — | Permanent token from your Meta app. |
| `WHATSAPP_PHONE_NUMBER_ID` | For WhatsApp | — | Cloud API phone number id. |
| `WHATSAPP_APP_SECRET` | For webhook | — | Webhook app secret (signature verification). |
| `MESSENGER_VERIFY_TOKEN` | For Messenger | — | Hub verify token (Messenger + Instagram share `/webhooks/meta`). |
| `MESSENGER_PAGE_TOKEN` | For Messenger | — | Page access token. |
| `INSTAGRAM_ACCESS_TOKEN` | For Instagram | — | Instagram Direct access token. |
| `GRAPH_API_VERSION` | No | `v24.0` | Meta Graph API version (bump in one place). |

## X (Twitter)

| Variable | Required | Default | Description |
|---|---|---|---|
| `X_BEARER_TOKEN` | For monitoring | — | Read-only app token. |
| `X_API_KEY` / `X_API_SECRET` | For posting | — | OAuth1 consumer key/secret. |
| `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | For posting | — | OAuth1 user access token/secret. |

## Lead discovery & AI

| Variable | Required | Default | Description |
|---|---|---|---|
| `SERPAPI_KEY` | No | — | SerpAPI key for business discovery. |
| `SEARXNG_URL` | No | — | Self-hosted SearXNG as alternative backend. |
| `LLM_URL` | No | `http://localhost:8080` | OpenAI-compatible endpoint for AI copy drafts (also configurable per-provider in Settings). |

## Rate limits & guards

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMAIL_RATE_PER_HOUR` | No | `300` | Max emails per hour (Brevo free tier = 300/day). |
| `TELEGRAM_RATE_PER_HOUR` | No | `25` | Max Telegram messages per hour. |
| `SMS_RATE_PER_HOUR` | No | `100` | Max SMS per hour (cost control). |
| `CRAWL_ALLOW_PRIVATE` | No | `0` | `1` lets the crawler target private/loopback addresses. Leave `0` unless crawling sites you own. |
| `ALLOW_PRIVATE_LLM` | No | `0` | `1` permits loopback/private base URLs for LLM providers and SearXNG (needed for a local Ollama/llama.cpp). Default denies private ranges incl. cloud metadata (SSRF guard). |

## Where the data lives

- SQLite file: `fixzy.db` (repo root) or `DATABASE_URL`. In Docker it is on the
  `fixzy-data` volume. **It contains personal data — never commit it** (already
  gitignored).
- `.env` holds secrets — also gitignored, never commit.
