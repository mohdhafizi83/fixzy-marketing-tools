# Fixzy Marketing Tools — Project Brief

Status: F1 BUILT (local dev) · Started: 6 Oct 2026 · Owner: Hafizi (AI Agentic for Hire)
Hermes profile: `fixzymarketingtool` (dedicated to this project only) · Target port: **:5558** (verified free)

## 1. What this is

Open-source portfolio tool: lead generation + multi-channel outreach. A modern
rebuild of the legacy app "EmailSpider" (VB.NET, Visual Studio 2015, .NET Framework 4.5.2,
last commit 17 Oct 2016) stored on an external HD:

    /mnt/workstation/Projects/standalone/Visual Studio 2015/Projects/FixzyMarketingTools/
    (NTFS "Workstation" — mount read-only: sudo mount -o ro /dev/sdb1 /mnt/workstation)

## 2. Legacy features kept (from a full code read, Oct 2026)

- Extract EMAIL + PHONE from 4 sources: .txt/.csv files, URL lists, text paste, full-website crawl (follows `<a href>`)
- Malaysian phone normalization: country code `6`, prefix `01`, strip junk characters (`-`, spaces, etc.)
- Dedup results during scraping
- Export to TXT/CSV
- Email blast via SMTP (SendGrid) and SMS via HTTP gateway
- Settings form for credentials

## 3. REMOVED / REPLACED

| Legacy | Why | Replacement |
|---|---|---|
| Google search `<cite>` scraping | Dead — Google blocks it | Search API (SerpAPI ~$0.0008/search) or SearXNG |
| sms99.net | Gateway long gone | New MY SMS gateway: Twilio / RedSMS / TMTxcel (~RM0.04–0.10/message) |
| Hardcoded expiry 1 Dec 2017 | Old app was sold locked | Removed — open source |
| Windows WinForms desktop | Platform-locked | Web UI (Flask), runs on a Linux server |
| Plaintext credentials in config | Security risk | .env + template; secrets never in git |

## 4. NEW features

- **Consent ledger + auto-unsubscribe** on every outbound (Malaysia PDPA 2010 — fines up to RM500k). This is a feature, not a burden.
- **Automatic suppression list** (email bounce / unsub → never bothered again)
- **Campaign analytics** — delivered / opened / failed per channel
- **AI copy drafts** — draft messages via local LLM `localhost:8080` (RM0 cost)
- **Channel capability flags** — every channel is marked with what it can actually do (see §6)

## 5. Tech stack (agreed 6 Oct 2026)

- Flask + Jinja/HTMX (web UI) — consistent with the existing Flask ecosystem (:5556, :5557)
- SQLite — leads, campaigns, consent, suppression
- APScheduler — blast scheduling + rate limiting
- selectolax / requests — crawler (replaces HtmlAgilityPack)
- aiosmtplib — email sender
- **Adapter pattern**: `adapters/brevo_email.py`, `adapters/twilio_sms.py`, `adapters/telegram_bot.py`, `adapters/whatsapp_cloud.py`
  — one interface: `send(lead, message, subject)`
- Port **:5558**, systemd user unit `fixzy-marketing-tools.service` (when deployed)

## 6. Channel reality (verified against official docs, Oct 2026)

NEVER build a "blast button" for a channel that does not support outbound — ban risk.

**TIER 1 — automatic outbound allowed:**
- Email: Brevo (300/hr free) / SendGrid (100/hr free) / Resend (3k/month free)
- SMS MY: Twilio / RedSMS / TMTxcel ~RM0.04–0.10/message
- Telegram Bot: RM0 — but only to users who have sent `/start` first

**TIER 2 — reply-only (24-hour window after the user messages us):**
- WhatsApp Cloud API (Meta): marketing template ~RM0.50/message (MY, since Jul 2025); requires Meta Business verification + template approval; cold blasting = numbers easily banned
- Facebook Messenger / Instagram DM: NO API for DMing strangers; Private Replies to comment replies only (7 days)

**TIER 3 — publish/monitor only (no DM API):**
- X/Twitter: pay-per-use ~$0.005/post read; can post + auto-reply to comments
- TikTok / YouTube: API for upload + reading comments/insights only

## 7. Phases

- **F1 (MVP, ~RM0):** crawler + lead DB + Email + Telegram + unsubscribe handling
- **F2:** MY SMS gateway + search API + analytics dashboard
- **F3:** WhatsApp Cloud API + FB/IG reply inbox + X/TikTok comment monitoring

> CONFIRMED DECISION (6 Oct 2026, owner): F1 = crawler + lead DB + Email + Telegram
> + consent ledger/auto-unsubscribe. Email provider: **Brevo** (300/hr free).
> GitHub: develop locally first, make public later.

## 8. Security warnings

- `akaun_detail.png` in the legacy folder **exposes old SendGrid/SMS credentials in plaintext** — do NOT publish/share; assume leaked.
- No real API keys in git. `.env` for secrets, `.env.example` as template.

## 9. How to start a development session

    fixzymarketingtool chat
    # or: hermes -p fixzymarketingtool chat

The profile working directory is already set to /home/fizi/projects/fixzy-marketing-tools/.
Read this file first, then continue with F1/F2.

## 10. Running it (F1)

    cd /home/fizi/projects/fixzy-marketing-tools
    cp .env.example .env   # fill in Brevo SMTP key, Telegram token
    .venv/bin/python app.py
    # UI: http://<server-lan-ip>:5558
