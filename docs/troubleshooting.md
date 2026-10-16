# Troubleshooting — Fixzy Marketing Tools

**Container unhealthy / restarts in a loop**
`docker compose logs app`. Common causes: missing `.env` (compose needs it —
`cp .env.example .env`), or `DATABASE_URL` pointing somewhere unwritable.
The healthcheck hits `GET /healthz` inside the container.

**Port already in use**
Another service owns 5558. Run on another port: `APP_PORT=18084 docker compose up -d`.

**403 "Forbidden: set ADMIN_PASSWORD"**
`ADMIN_PASSWORD` is empty, so the UI only answers LAN clients. Set a password
in `.env` (or access from the same machine).

**401 immediately after login**
Basic auth is checked on every request; a typo in `ADMIN_USER`/`ADMIN_PASSWORD`
or too many failed attempts (per-IP lockout, wait a minute) both cause this.

**Sessions/CSRF break after every restart**
`SECRET_KEY` is unset — the app generates an ephemeral one and prints a
warning. Set a permanent one: `openssl rand -hex 32`.

**Sends silently skip leads**
By design: a lead is skipped if it lacks an active consent record for that
channel or is on the suppression list. Check the campaign result and
`docs/pdpa-compliance.md`.

**Local LLM (Ollama etc.) refused in Settings**
The SSRF guard denies private/loopback URLs by default. If the LLM runs on a
host you own, set `ALLOW_PRIVATE_LLM=1`.

**Unsubscribe links point to localhost**
Set `PUBLIC_BASE_URL` to your public URL in `.env`.
