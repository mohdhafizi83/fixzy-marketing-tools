# Security Policy

Fixzy Marketing Tools is an admin-authenticated outreach app meant to run on
a LAN/VPN or behind a TLS reverse proxy. This document describes the threat
model, the controls in place, and how to report vulnerabilities.

## Reporting a vulnerability

Open a [private security advisory](https://github.com/mohdhafizi83/fixzy-marketing-tools/security/advisories/new).
Do not file public issues for unfixed vulnerabilities.

## Threat model

| # | Threat | Control | Where | Test |
|---|--------|---------|-------|------|
| 1 | CSRF on state-changing routes (settings, campaigns, imports) | Session CSRF token, `hmac.compare_digest`, required on every non-GET except provider webhooks (which use their own signatures) | `app.py` `csrf_protect` | `test_post_without_csrf_rejected`, `test_webhooks_exempt_from_csrf` |
| 2 | Forged WhatsApp/Meta webhook events | `X-Hub-Signature-256` HMAC over the raw body, mandatory when the app secret is configured; missing secret → 403 (fail closed); empty never matches empty | `app.py` webhooks | `test_whatsapp_tampered_signature_rejected`, `test_meta_webhook_fail_closed` |
| 3 | Forged Brevo event webhook | Shared secret via `?key=`, constant-time compare, fail closed when unset | `app.py` `brevo_webhook` | `test_brevo_fail_closed_when_secret_unset`, `test_brevo_wrong_key_rejected` |
| 4 | Forged Telegram `/start` (fake consent) | `X-Telegram-Bot-Api-Secret-Token` must match when configured (fail closed) | `app.py` `telegram_webhook` | `test_telegram_webhook_fails_closed_when_secret_set` |
| 5 | SSRF via crawler (cloud metadata 169.254.169.254, internal LAN) | `netguard.check_url_allowed`: http/https only, no userinfo, resolve via `getaddrinfo`, reject private/loopback/link-local/reserved; DNS failure fails closed; redirects re-checked hop-by-hop | `netguard.py`, `crawler.py` | `test_crawler_blocks_metadata_ip`, `test_import_crawl_mode_refuses_private_target` |
| 6 | SSRF via user-configured LLM `base_url` / SearXNG URL (Settings UI) | Same guard at save time (rejected with flash) and at request time; `ALLOW_PRIVATE_LLM=1` is the documented escape for a local Ollama/llama.cpp | `aicopy.py`, `searchapi.py`, `app.py` | `test_llm_provider_add_rejects_private_url`, `test_llm_draft_refuses_private_provider_without_network`, `test_searxng_private_url_blocked_without_network` |
| 7 | Session/CSRF forgery via a hardcoded default secret | No hardcoded `SECRET_KEY`: unset → strong ephemeral key per process + startup warning (sessions reset on restart until the operator sets one) | `config.py` | `test_secret_key_generated_when_unset` |
| 8 | Admin password guessing | Basic auth with constant-time compare; 10 failed logins/min per IP → 429 (only failures count); no password configured → LAN-only, public callers get 403 | `app.py` `require_admin_auth` | `test_failed_logins_rate_limited_but_success_always_ok`, `test_wrong_password_rejected` |
| 9 | Webhook endpoint flooding | In-memory fixed-window limiter: 60 req/min per IP on `/webhooks/*` and `/telegram/webhook` → 429 before signature work | `ratelimit.py` | `test_webhook_rate_limited` |
| 10 | Memory exhaustion via huge uploads | `MAX_CONTENT_LENGTH` 1 MB → generic 413; crawler caps pages at 2 MB streamed | `app.py`, `crawler.py` | `test_oversize_body_rejected_413` |
| 11 | Clickjacking / MIME sniffing / data exfil via referrer | CSP `default-src 'none'` + `frame-ancestors 'none'`, `X-Frame-Options DENY`, `nosniff`, `Referrer-Policy no-referrer`, `X-XSS-Protection 0`, Permissions-Policy | `app.py` `set_security_headers` | `test_csp_default_src_none_and_lockdowns`, `test_security_headers_present` |
| 12 | Traceback/host leak in error pages | Generic 413/500 handlers; exception text logged server-side only | `app.py` error handlers | `test_internal_error_never_leaks_traceback` |
| 13 | Lead data cached by shared browsers/proxies | `Cache-Control: no-store` on settings/campaign/inbox/export/webhook responses | `app.py` | `test_cache_control_no_store_on_settings_and_api` |
| 14 | Dependency vulnerabilities / supply chain | Fully pinned `requirements.txt`; CI runs pip-audit, bandit, ruff, gitleaks; Actions pinned to full SHAs | `.github/workflows/ci.yml` | CI |
| 15 | Contact without consent (PDPA) | Consent ledger + suppression table gate every blast; unsubscribe/bounce/spam webhooks revoke automatically | `models.py`, `scheduler.py` | `test_no_consent_never_eligible`, `test_brevo_unsubscribe_revokes_consent` |

## Fail-closed statements

- Webhook secret unset → the webhook refuses all traffic (403), it is never
  "open until configured".
- `SECRET_KEY` unset → ephemeral random key + loud warning; never a static
  default. Note: with a rotating per-process key, session CSRF tokens do not
  survive restarts and do not work across multiple workers — set a fixed
  `SECRET_KEY` (`openssl rand -hex 32`) in production.
- `ADMIN_PASSWORD` unset → the UI is LAN-only; non-LAN callers get 403.
- SSRF guard: DNS failure or any private/reserved resolution → refuse.
  Escape hatches (`ALLOW_PRIVATE_LLM=1`, `CRAWL_ALLOW_PRIVATE=1`) are
  opt-in, documented, and intended only for hosts you own.

## CSP note (honest scoping)

`default-src 'none'` with `script-src 'self' 'unsafe-inline'` and
`style-src 'self' 'unsafe-inline'`: every template embeds inline
`<script>`/`<style>` (no static asset build step exists), so inline is
scoped to exactly those two sources and everything else (objects, frames,
base tags, form targets, connections) is locked. The app is single-admin;
the residual XSS surface is the admin's own session.

## Out of scope

- Multi-user auth/RBAC (single admin by design).
- Encryption at rest (SQLite file; protect with filesystem permissions).
- Distributed rate limiting (limiter is per-process by design; put nginx
  `limit_req` in front for real floods).
- Provider-side abuse (message templates must follow each platform's
  policies — see PROVIDER_COMPLIANCE.md).

## Reject-path demos (curl)

```bash
BASE=http://127.0.0.1:5558
AUTH='-a admin:PASSWORD'

# 1. CSRF: state-changing POST without token -> 400
curl -s $AUTH -o /dev/null -w '%{http_code}\n' -X POST $BASE/campaign/new \
     -d 'name=x&channel=email&message=hi'                     # 400

# 2. Oversize body -> 413
head -c 2000000 /dev/zero | tr '\0' 'x' > /tmp/big.txt
curl -s $AUTH -o /dev/null -w '%{http_code}\n' -X POST $BASE/import \
     -F mode=file -F file=@/tmp/big.txt                       # 413

# 3. Headers present on every response
curl -s $AUTH -D- -o /dev/null $BASE/ | grep -iE \
  'content-security|x-frame|referrer|permissions|x-xss'       # all present

# 4. Unsigned webhook -> 401 (secret configured) / 403 (unset)
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE/webhooks/whatsapp \
     -H 'Content-Type: application/json' -d '{"entry":[]}'    # 401/403

# 5. SSRF-blocked LLM provider (Settings -> LLM, or API)
curl -s $AUTH -o /dev/null -w '%{http_code}\n' -X POST $BASE/settings/llm \
     -d 'action=add&name=evil&base_url=http://169.254.169.254/v1'  # 302 + "not saved" flash
```
