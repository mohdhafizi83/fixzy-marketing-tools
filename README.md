# Fixzy Marketing Tools
[![CI](https://github.com/mohdhafizi83/fixzy-marketing-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/mohdhafizi83/fixzy-marketing-tools/actions/workflows/ci.yml)


Open-source lead generation + multi-channel outreach tool. A modern Flask rebuild
of a 2016 VB.NET desktop app ("EmailSpider"), redesigned around one principle:
**outreach without consent tracking is a liability — so consent is built in.**

Compliance-first: every outbound message carries an unsubscribe link, every
consent grant/revocation is recorded in a ledger (Malaysia PDPA 2010 aware),
and unsubscribed/bounced contacts are automatically suppressed.

Stack: Flask + SQLite + web UI, port `:5558`. No paid infrastructure required.

## Features

**Lead capture**
- Extract emails + phone numbers from 4 sources: pasted text, uploaded
  .txt/.csv files, URL lists, and polite full-site crawling (respects
  `robots.txt`, configurable delay/page/depth caps)
- Search-API discovery: query → top result URLs → crawl for contacts
  (SerpAPI or self-hosted SearXNG)
- Malaysian phone normalization (`012-345 6789` → `60123456789`), dedup on
  every import
- CSV / TXT export

**Compliance (PDPA 2010, Malaysia)**
- Consent ledger: every grant/revocation recorded with timestamp and source,
  never deleted — auditable forever
- Automatic suppression: unsubscribe click, email bounce, or spam complaint
  → contact is never bothered again
- Mandatory unsubscribe in every outbound: `List-Unsubscribe` header +
  visible link (email), STOP footer (SMS)
- Public unsubscribe pages require no login (recipients aren't admins)

**Channels** (capability flags enforced in code — see safety model below)
- Email via Brevo SMTP relay (free tier 300/day)
- Telegram bot (free; opt-in only — users must `/start` first)
- SMS via Twilio or RedSMS (Malaysian gateway)
- WhatsApp Cloud API — reply-only by design (24h window / approved templates)
- Facebook Messenger + Instagram Direct — reply-only (24h window)
- X/Twitter — publish, monitor, and reply to posts (no cold DMs by design)

**Operations**
- Reply Inbox: all inbound messages (WhatsApp/Messenger/IG) in one screen with
  inline reply
- Campaign scheduling (APScheduler) with per-channel hourly rate caps
- Analytics: sent / delivered / opened / bounced / failed per channel and
  per campaign, plus suppression breakdown and recent-failure debug view
- AI copy drafts via any OpenAI-compatible LLM endpoint (local llama.cpp /
  Ollama = free, or cloud providers)
- All provider credentials managed from the web UI (Settings → Channels) —
  DB-first with `.env` fallback, no restart needed

## Quick start

**Docker (recommended):**

```bash
git clone https://github.com/mohdhafizi83/fixzy-marketing-tools.git
cd fixzy-marketing-tools
cp .env.example .env      # set at least SECRET_KEY + ADMIN_PASSWORD
docker compose up -d --build
# UI: http://localhost:5558  (APP_PORT=xxxx to change the host port)
```

**Native:**

```bash
git clone <repo-url> && cd fixzy-marketing-tools
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # optional: fill credentials, or do it in the UI later
.venv/bin/python app.py
# UI: http://localhost:5558
```

Without any credentials the app still runs: channels show as
"not configured" and nothing is sent. Add keys anytime via
**Settings → Channels** (takes effect immediately).

## Documentation

- [Getting started](docs/getting-started.md) — Docker quickstart + first campaign
- [Configuration](docs/configuration.md) — every environment variable
- [PDPA compliance guide](docs/pdpa-compliance.md) — consent ledger, suppression, direct-marketing duties (Malaysia)
- [Troubleshooting](docs/troubleshooting.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## First login (admin auth)

The UI holds lead data and settings, so it is protected by HTTP Basic auth.

- Set `ADMIN_USER` and `ADMIN_PASSWORD` in `.env` (any values you choose),
  then start/restart the app.
- **If `ADMIN_PASSWORD` is empty, the app fails closed:** only private
  networks (127.x / 10.x / 192.168.x / 100.x) may access the UI; anything
  from the public internet gets 403 until you set a password. There is no
  default password and no backdoor.
- Public exceptions by design: `/unsubscribe/*` (recipients are not admins)
  and `/webhooks/*` (providers call them; each webhook has its own
  verification — see below).

## Security

Full threat model, control matrix, and fail-closed statements:
**[SECURITY.md](SECURITY.md)**. Highlights:

- **CSRF**: session token enforced on every state-changing request
  (`hmac.compare_digest`); provider webhooks are exempt by design and use
  their own signature verification instead.
- **Webhook signatures**: WhatsApp/Meta require `X-Hub-Signature-256` when
  the app secret is set; Brevo uses a constant-time shared key; Telegram
  checks `X-Telegram-Bot-Api-Secret-Token`. All fail closed when the secret
  is unset — an unconfigured webhook is a dead webhook, never an open one.
- **SSRF guard**: crawler, LLM provider URLs, and self-hosted SearXNG URLs
  are checked against private/loopback/link-local ranges (incl. cloud
  metadata `169.254.169.254`); redirects are re-checked hop-by-hop. For a
  local Ollama/llama.cpp server set `ALLOW_PRIVATE_LLM=1` (documented,
  default deny).
- **Headers**: CSP `default-src 'none'` (inline script/style scoped
  honestly — see SECURITY.md), `X-Frame-Options DENY`, `nosniff`,
  `no-referrer`, `X-XSS-Protection 0`, `Cache-Control: no-store` on
  settings/API routes.
- **Limits**: 1 MB request body cap (413), 60 req/min per IP on webhooks,
  10 failed admin logins/min per IP (429).
- **Supply chain**: fully pinned `requirements.txt`; CI (SHA-pinned Actions)
  runs pytest, ruff, bandit, pip-audit, and gitleaks.

Reject-path demos (recruiter-visible proof):

```bash
# CSRF without token -> 400
curl -s -a admin:PW -o /dev/null -w '%{http_code}\n' -X POST \
     http://127.0.0.1:5558/campaign/new -d 'name=x&channel=email&message=hi'
# unsigned webhook -> 401/403
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
     http://127.0.0.1:5558/webhooks/whatsapp -H 'Content-Type: application/json' -d '{}'
# SSRF-refusing LLM URL -> not saved
curl -s -a admin:PW -X POST http://127.0.0.1:5558/settings/llm \
     -d 'action=add&name=evil&base_url=http://169.254.169.254/v1' -o- | grep -o 'not saved[^<]*'
```

## Webhook security

- Meta webhooks (`/webhooks/whatsapp`, `/webhooks/meta`): hub.challenge
  handshake with your verify token (empty never matches empty), plus
  `X-Hub-Signature-256` HMAC verification when the header is present
  (constant-time compare; mismatch → 401).
- Brevo events (`/webhooks/brevo?key=<secret>`): shared secret; register
  the URL in your Brevo dashboard to receive delivered/opened/bounce/spam
  events that feed suppression and analytics automatically.
- Telegram: point your bot's webhook at `/telegram/webhook`; `/start`
  registers chat_id + consent.

## Channel safety model

This tool deliberately refuses to build "blast buttons" for channels that do
not support outbound sending (ban risk). WhatsApp/Messenger/Instagram are
reply-only in code (`send()` refuses; only `send_reply()`/`send_template()`
work). X has no per-lead sending at all. See the tier table in
[PROJECT_BRIEF.md](PROJECT_BRIEF.md) §6 and the full audit in
[PROVIDER_COMPLIANCE.md](PROVIDER_COMPLIANCE.md) — every endpoint, auth
scheme, and payload shape checked against official provider docs (Oct 2026),
with sources cited and known gaps listed honestly.

## Configuration

All secrets live in `.env` (never committed). See `.env.example` for the full
list. Key variables:

| Variable | Purpose |
|---|---|
| `ADMIN_USER` / `ADMIN_PASSWORD` | UI login (required for public exposure) |
| `BREVO_SMTP_USER` / `BREVO_SMTP_KEY` | Brevo SMTP relay credentials |
| `MAIL_FROM` | From address (must be a verified sender domain in Brevo) |
| `BREVO_WEBHOOK_SECRET` | Shared secret for delivery/bounce event webhook |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TWILIO_*` / `REDSMS_*` | SMS gateway credentials |
| `WHATSAPP_*` / `MESSENGER_*` / `INSTAGRAM_*` | Meta platform credentials |
| `X_*` | X API (bearer for read; 4-legged OAuth1 for publish/reply) |
| `SERPAPI_KEY` / `SEARXNG_URL` | Search backend for lead discovery |
| `GRAPH_API_VERSION` | Meta Graph API version (default v24.0, valid to 2028) |
| `PUBLIC_BASE_URL` | Public URL used in unsubscribe links — **must be reachable by recipients** |
| `EMAIL_RATE_PER_HOUR` | Blast rate cap (Brevo free = 300/day) |

Every one of these can also be set in **Settings → Channels** (stored in the
DB, overrides `.env`).

## Testing

```bash
.venv/bin/pytest tests/
```

58 tests covering: extractor edge cases (MY phone rules), the PDPA consent +
suppression eligibility gate, webhook fail-closed behavior, webhook
signature forgery rejection, CSRF, security headers, SSRF accept/reject
paths, rate limiting, and error hygiene. Uses a throwaway SQLite DB — never
touches your data. CI (GitHub Actions) runs the same suite plus ruff,
bandit, pip-audit, and gitleaks on every push.

## Deployment (reference setup)

- systemd user unit: `~/.config/systemd/user/fixzy-marketing-tools.service`
  (`systemctl --user enable --now fixzy-marketing-tools`)
- HTTPS without buying a certificate: Tailscale Funnel —
  `tailscale funnel --bg 5558` (the `--bg` flag persists the config)
- Set `PUBLIC_BASE_URL` to your public HTTPS URL so unsubscribe links work
  from the internet
- Any reverse proxy (nginx/Caddy) works equally well; the app binds
  `0.0.0.0:5558`

## Important legal notes

- Scraped emails are **not** consent. The tool records crawled leads with a
  source tag so you can audit where each contact came from. Check your local
  law (Malaysia PDPA 2010, GDPR, CAN-SPAM) before messaging any list.
- `PUBLIC_BASE_URL` must point at a URL recipients can actually open, or
  unsubscribe links are broken — which defeats the compliance feature.
- Email deliverability requires a sender domain you own with SPF/DKIM/DMARC
  configured in your provider. Sending from shared/free addresses lands in
  spam.
- This project is provided as-is; you are responsible for how you use it.

## Roadmap

- **F1 (built):** crawler + lead DB + Email + Telegram + consent/unsubscribe
- **F2 (built):** MY SMS gateway + search API + analytics dashboard
- **F3 (built):** WhatsApp Cloud API (reply-only) + Messenger/Instagram Direct
  reply inbox + X monitoring
- **Provider compliance (audited):** see
  [PROVIDER_COMPLIANCE.md](PROVIDER_COMPLIANCE.md) — includes 5 known gaps
  open for contributors (RedSMS format verification, TikTok/YouTube
  monitoring, FB/IG Private Replies, Brevo marketing-campaign events,
  self-hosted open pixel)
- **Deployment (documented above):** systemd + HTTPS funnel + admin auth

## License

MIT — see [LICENSE](LICENSE).
