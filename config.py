"""Central configuration — all secrets come from .env, nothing hardcoded."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Fail-closed secret key: a hardcoded fallback would let anyone forge session
# cookies / CSRF tokens. If unset, generate a strong ephemeral key per process
# (sessions simply do not survive restarts until the operator sets one).
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY is not set in .env — generated an ephemeral "
          "one. Sessions/CSRF tokens will not survive restarts. "
          "Generate with: openssl rand -hex 32")
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'fixzy.db'}"
)

# Brevo SMTP relay (docs: developers.brevo.com/docs/smtp-integration)
BREVO_SMTP_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
BREVO_SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
BREVO_SMTP_USER = os.getenv("BREVO_SMTP_USER", "")      # SMTP login email
BREVO_SMTP_KEY = os.getenv("BREVO_SMTP_KEY", "")        # SMTP key
MAIL_FROM = os.getenv("MAIL_FROM", "")

# Telegram bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Optional shared secret sent by Telegram as X-Telegram-Bot-Api-Secret-Token
# when the webhook is registered with secret_token. When set, the webhook
# FAILS CLOSED: requests without a matching header are rejected.
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

# Twilio SMS (Tier 1, verified vs twilio.com/docs)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")   # e.g. +60123456789

# RedSMS MY (format NOT verified against official docs — see adapter docstring)
REDSMS_USERNAME = os.getenv("REDSMS_USERNAME", "")
REDSMS_PASSWORD = os.getenv("REDSMS_PASSWORD", "")
REDSMS_SENDER_ID = os.getenv("REDSMS_SENDER_ID", "Fixzy")

# Search API for lead source discovery (F2)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "")   # self-hosted alternative

# --- F3: WhatsApp Cloud API (Meta) ----------------------------------------
# Verified vs developers.facebook.com (Oct 2026): reply-only within the 24h
# customer-service window; template messages for business-initiated contact.
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")   # webhook verification

# --- F3: X (Twitter) API v2 ----------------------------------------------
# Verified vs docs.x.com (Oct 2026): pay-per-use, POST /2/tweets to publish.
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")        # read (monitoring)
X_API_KEY = os.getenv("X_API_KEY", "")                  # consumer key (OAuth1)
X_API_SECRET = os.getenv("X_API_SECRET", "")            # consumer secret
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")        # user access token
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET", "")      # user access secret

# Meta Graph API version used by WhatsApp/Messenger/Instagram adapters.
# Verified vs developers.facebook.com/docs/graph-api/changelog (Oct 2026):
# v24.0 released Oct 8 2025, available until Feb 18 2028. Bump this single
# constant when Meta releases a newer version.
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v24.0")

# Meta messaging: Messenger (FB Page) + Instagram Direct share one webhook
MESSENGER_VERIFY_TOKEN = os.getenv("MESSENGER_VERIFY_TOKEN", "")
MESSENGER_PAGE_TOKEN = os.getenv("MESSENGER_PAGE_TOKEN", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

# Shared secret for the Brevo event webhook (/webhooks/brevo?key=<secret>)
BREVO_WEBHOOK_SECRET = os.getenv("BREVO_WEBHOOK_SECRET", "")

# Admin auth (required before any public exposure — funnel/HTTPS)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Unsubscribe links must use a publicly reachable URL so recipients can click them
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5558")

# Rate cap per channel per hour (Brevo free tier = 300/day; override per your account)
RATE_LIMITS_PER_HOUR = {
    "email": int(os.getenv("EMAIL_RATE_PER_HOUR", "300")),
    "telegram": int(os.getenv("TELEGRAM_RATE_PER_HOUR", "25")),  # Telegram allows ~30/s globally; we stay conservative
    "sms": int(os.getenv("SMS_RATE_PER_HOUR", "100")),           # cost control: SMS is paid per message
}

# AI copy drafts (local LLM, optional F1 hook)
LLM_URL = os.getenv("LLM_URL", "http://localhost:8080")

# SSRF guard: the crawler refuses private/loopback/link-local/reserved targets
# (cloud metadata endpoints, internal LAN services). Set CRAWL_ALLOW_PRIVATE=1
# only if you deliberately crawl internal sites you own.
CRAWL_ALLOW_PRIVATE = os.getenv("CRAWL_ALLOW_PRIVATE", "") == "1"
