# Getting Started — Fixzy Marketing Tools

Self-hosted lead generation + multi-channel outreach (email, Telegram, SMS,
WhatsApp, Messenger/Instagram, X) with a built-in PDPA consent ledger and
suppression list.

## Requirements

- Docker + Docker Compose (recommended)
- OR: Python 3.12 with pip

## Quickstart (Docker — recommended)

```bash
git clone https://github.com/mohdhafizi83/fixzy-marketing-tools.git
cd fixzy-marketing-tools
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and ADMIN_PASSWORD:
#   SECRET_KEY:   openssl rand -hex 32
#   ADMIN_PASSWORD: something strong (the UI is Basic-auth protected)
docker compose up -d --build
```

Open **http://localhost:5558** and log in with `ADMIN_USER` /
`ADMIN_PASSWORD` from your `.env`. To use another host port:
`APP_PORT=18084 docker compose up -d`.

First steps in the UI:

1. **Import** — paste a CSV/TXT list of emails/phones (or crawl a site under
   Settings → Search). Each imported contact gets a consent record per channel.
2. **Campaign** — compose a message, pick a channel, send or schedule. Leads
   without consent or on the suppression list are skipped automatically.
3. **Analytics / Inbox** — track sends and answer replies.

The database lives on the `fixzy-data` named volume (`/data/fixzy.db` in the
container), so it survives rebuilds: `docker compose down` keeps your data;
`docker compose down -v` deletes it.

## Install without Docker

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edit as above
python app.py             # serves on http://localhost:5558
```

Run the tests with `pytest tests -q`.

## Next steps

- [Configuration](configuration.md) — every environment variable
- [PDPA compliance guide](pdpa-compliance.md) — consent ledger, suppression,
  direct-marketing rules in Malaysia
- [SECURITY.md](../SECURITY.md) — hardening model and reporting issues
- [Troubleshooting](troubleshooting.md) — common issues
