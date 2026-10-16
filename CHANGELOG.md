# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-16

First product-grade release.

### Added
- Lead generation: CSV/TXT import with dedup, web crawler + search-API
  discovery (SerpAPI / self-hosted SearXNG), X (Twitter) monitor.
- Multi-channel outreach: email (Brevo SMTP), Telegram bot, SMS (Twilio /
  RedSMS), WhatsApp Cloud API, Messenger + Instagram Direct, X posts —
  all reply-window and rate-cap aware.
- PDPA (Malaysia) compliance core: consent ledger with per-channel grant
  records, suppression list, one-click unsubscribe links, per-channel
  rate limits. See `docs/pdpa-compliance.md`.
- Campaign scheduler (APScheduler) with draft/scheduled/send states and
  per-lead suppression gating.
- Inbox for inbound replies (Telegram/WhatsApp/Messenger) with in-UI reply.
- Analytics: per-campaign send/open/bounce/fail events via provider webhooks
  (Brevo, Telegram) with signature verification.
- Security hardening: CSRF on all state-changing routes, HTTP Basic admin
  auth with constant-time compare + lockout, SSRF guards (crawler, LLM
  providers, SearXNG), webhook rate limiting, 1MB body cap, security
  headers, fail-closed secrets. See `SECURITY.md`.
- Docker: `Dockerfile` + `docker-compose.yml` with healthcheck
  (`GET /healthz`), non-root user, named volume for the sqlite DB.
- Docs: `docs/getting-started.md` (Docker quickstart),
  `docs/configuration.md` (every env var), `docs/pdpa-compliance.md`.
- UI: self-hosted design system (Tabler Core + Fixzy design tokens,
  dark-first). No external CDNs.
- CI (pytest + ruff + bandit + pip-audit + gitleaks, SHA-pinned actions)
  and a tag-triggered Release workflow publishing to GitHub Releases + GHCR.
