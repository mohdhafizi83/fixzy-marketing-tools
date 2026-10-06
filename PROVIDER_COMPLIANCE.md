# Provider API Compliance Audit

Every outbound/inbound integration in this repo, checked against the
provider's OFFICIAL documentation. Last audit: October 2026.
When you change an adapter, update this table too.

Legend:
- **Verified** = endpoint, auth, and payload checked against official docs
  (source cited). Code follows the documented contract.
- **Unverified** = built from widely-circulated formats because official
  docs were unreachable at build time. Treat as needing confirmation.
- **Untested with live credentials** = no real account was used. The code
  follows the documented contract; actual delivery depends on valid keys,
  approved templates, and platform-side setup.

| Channel | Endpoint(s) | Auth | Status | Official source |
|---|---|---|---|---|
| Email (Brevo) | `smtp-relay.brevo.com:587` STARTTLS | SMTP login email + SMTP key | Verified, live-tested (delivery gated by sender-domain reputation) | help.brevo.com, developers.brevo.com/docs/smtp-integration |
| Brevo events | `POST /webhooks/brevo?key=<secret>` (our side) | shared secret query param; fail-closed when unset | Verified payload shapes (delivered/opened/click/soft_bounce/hard_bounce/spam/unsubscribed/blocked/request/deferred/error) | developers.brevo.com/docs/transactional-webhooks |
| Telegram | `https://api.telegram.org/bot<token>/sendMessage` | bot token in URL path | Verified (Bot API 10.x; `chat_id`+`text` stable across versions) | core.telegram.org/bots/api |
| SMS (Twilio) | `POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json` | HTTP Basic (SID : AuthToken), form params To/From/Body | Verified | twilio.com/docs/messaging/api/message-resource |
| SMS (RedSMS) | `GET https://www.redsms.com/api/sendsms.php` | username/password params | **UNVERIFIED** — redsms.com unreachable at build time (SSL error). Format from widely-circulated convention. Confirm against the docs you receive with your account before trusting. | none reachable (Oct 2026) |
| WhatsApp Cloud | `https://graph.facebook.com/{V}/{PHONE_NUMBER_ID}/messages` | Bearer token | Verified; version pinned via `GRAPH_API_VERSION` (v24.0, available until 18 Feb 2028 per changelog) | developers.facebook.com/docs/graph-api/changelog |
| Messenger / IG Direct | `https://graph.facebook.com/{V}/me/messages` (`messaging_type: RESPONSE`) | Bearer (Page / IG token) | Verified | developers.facebook.com Messenger Platform docs |
| X publish/reply | `POST https://api.x.com/2/tweets` (`reply.in_reply_to_tweet_id` for replies) | OAuth1 4-legged (consumer key+secret, access token+secret) | Verified | docs.x.com/x-api/posts/manage-tweets |
| X search | `GET https://api.x.com/2/tweets/search/recent` (max_results 10–100) | Bearer | Verified | docs.x.com/x-api/posts/search-recent-posts |

## Webhook security (all providers)

- **Handshake (GET)**: `hub.mode=subscribe` + `hub.verify_token` must match
  the configured secret; empty secret NEVER matches (fail closed, 403).
- **Signature (POST)**: Meta webhooks (`/webhooks/whatsapp`, `/webhooks/meta`)
  verify `X-Hub-Signature-256 = sha256=HMAC-SHA256(raw_body, secret)` when
  the header is present; mismatch → 401. Constant-time comparison
  (`hmac.compare_digest`).
- **Brevo webhook**: shared secret via `?key=`; Brevo additionally documents
  IP-range allowlisting as a second layer (help.brevo.com).
- **Telegram webhook**: our `/telegram/webhook` accepts the Bot API update
  shape; set your webhook URL via BotFather or the setWebhook API.

## Platform rules enforced in code (not just documented)

- WhatsApp/Messenger/Instagram are **reply-only**: `send()` refuses blasts;
  only `send_reply()` (24h window) / `send_template()` (approved template)
  exist. Cold outreach has no supported API on these platforms.
- X has **no per-lead sending**: publish + monitor + reply-to-post only.
  DM automation is deliberately absent (no affordable tier supports it).
- Every email carries `List-Unsubscribe` header + visible link; every SMS
  carries a STOP footer. Unsubscribe/bounce/complaint events flow into the
  suppression list automatically (PDPA 2010, Malaysia).

## Known gaps (open for contributors)

1. **RedSMS format unverified** — see table above.
2. **TikTok / YouTube monitoring** — mentioned in the project brief, not
   implemented. TikTok Display API requires app approval before keys exist;
   contributions welcome against the official docs.
3. **FB/IG Private Replies** (comment→DM, 7-day) — not implemented; the
   inbox model supports the channel field already.
4. **Brevo marketing-campaign webhooks** (vs transactional) — we handle
   transactional events; campaign-level events use a different payload.
5. **Open tracking via pixel** — we rely on Brevo's `opened` webhook events;
   no self-hosted tracking pixel (deliberate: fewer privacy surfaces).

## How to verify a claim yourself

Each adapter's module docstring cites its source. The test suite
(`tests/`) encodes the security-critical behaviors:
`pytest tests/` — includes webhook signature forgery tests, consent-gate
tests, and fail-closed checks.
