# Fixzy Marketing Tools

Open-source lead generation + multi-channel outreach tool. A modern Flask rebuild
of a 2016 VB.NET desktop app ("EmailSpider"), redesigned around one principle:
**outreach without consent tracking is a liability — so consent is built in.**

Compliance-first: every outbound message carries an unsubscribe link, every
consent grant/revocation is recorded in a ledger (Malaysia PDPA 2010 aware),
and unsubscribed/bounced contacts are automatically suppressed.

## Features (F1)

- **Lead extraction** from 4 sources: pasted text, uploaded .txt/.csv files,
  URL lists, and polite full-site crawling (follows `<a href>`, respects
  `robots.txt`, configurable delay/page/depth caps)
- **Malaysian phone normalization** — `012-345 6789` → `60123456789`
- **Deduplication** on import and crawl
- **Consent ledger** — every grant/revocation recorded, never deleted (auditable)
- **Suppression list** — unsubscribe or bounce → never contacted again
- **Email via Brevo SMTP relay** (free tier: 300/day) with mandatory
  `List-Unsubscribe` header and in-body unsubscribe link
- **Telegram bot** — free, opt-in only (users must `/start` the bot first)
- **Rate-limited blasts** — per-channel hourly caps
- **CSV / TXT export** of leads

## Channel safety model

This tool deliberately refuses to build "blast buttons" for channels that do
not support outbound sending (ban risk). See the tier table in
[PROJECT_BRIEF.md](PROJECT_BRIEF.md) §6 — verified against official provider
docs (Oct 2026).

## Quick start

```bash
git clone <repo-url> && cd fixzy-marketing-tools
python3 -m venv .venv
.venv/bin/pip install flask flask-sqlalchemy aiosmtplib apscheduler requests selectolax python-dotenv
cp .env.example .env      # fill in your Brevo SMTP key and/or Telegram token
.venv/bin/python app.py
# UI: http://localhost:5558
```

Without credentials the app still runs; channels simply show as
"not configured" and no mail is sent.

## Configuration

All secrets live in `.env` (never committed). See `.env.example` for the full
list. Key variables:

| Variable | Purpose |
|---|---|
| `BREVO_SMTP_USER` / `BREVO_SMTP_KEY` | Brevo SMTP relay credentials |
| `MAIL_FROM` | From address (must be a verified sender domain in Brevo) |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `PUBLIC_BASE_URL` | Public URL used in unsubscribe links — **must be reachable by recipients** |
| `EMAIL_RATE_PER_HOUR` | Blast rate cap (Brevo free = 300/day) |

## Important legal notes

- Scraped emails are **not** consent. The tool records crawled leads with a
  source tag so you can audit where each contact came from. Check your local
  law (Malaysia PDPA 2010, GDPR, CAN-SPAM) before blasting any list.
- `PUBLIC_BASE_URL` must point at a URL recipients can actually open, or
  unsubscribe links are broken — which defeats the compliance feature.
- This project is provided as-is; you are responsible for how you use it.

## Roadmap

- **F1 (built):** crawler + lead DB + Email + Telegram + consent/unsubscribe
- **F2 (built):** MY SMS gateway + search API + analytics dashboard
- **F3 (built):** WhatsApp Cloud API (reply-only) + reply inbox + X monitoring
- **Deployment (active):** systemd user unit `fixzy-marketing-tools.service` +
  Tailscale funnel HTTPS (`tailscale funnel --bg 5558`). Admin login required
  for all UI paths except unsubscribe pages and provider webhooks
  (`ADMIN_USER`/`ADMIN_PASSWORD` in .env). LAN access also requires the
  password once set.

## License

MIT — see [LICENSE](LICENSE).
