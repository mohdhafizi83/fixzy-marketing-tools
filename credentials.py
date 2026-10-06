"""Credential resolution: Settings UI (DB) first, .env as fallback.

Every adapter reads credentials through cred() so users can configure the
whole tool from the web UI. The .env file remains a valid default path for
advanced deployments (Docker, config management), but is never required.

DB keys are lowercase snake_case, mirroring the env variable names.
"""
import config

# Maps DB key -> env-backed default from config.py
_ENV_DEFAULTS = {
    # Email (Brevo SMTP relay)
    "brevo_smtp_user": lambda: config.BREVO_SMTP_USER,
    "brevo_smtp_key": lambda: config.BREVO_SMTP_KEY,
    "mail_from": lambda: config.MAIL_FROM,
    # Telegram
    "telegram_bot_token": lambda: config.TELEGRAM_BOT_TOKEN,
    "telegram_webhook_secret": lambda: config.TELEGRAM_WEBHOOK_SECRET,
    # Twilio SMS
    "twilio_account_sid": lambda: config.TWILIO_ACCOUNT_SID,
    "twilio_auth_token": lambda: config.TWILIO_AUTH_TOKEN,
    "twilio_from_number": lambda: config.TWILIO_FROM_NUMBER,
    # RedSMS
    "redsms_username": lambda: config.REDSMS_USERNAME,
    "redsms_password": lambda: config.REDSMS_PASSWORD,
    "redsms_sender_id": lambda: config.REDSMS_SENDER_ID,
    # WhatsApp Cloud
    "whatsapp_access_token": lambda: config.WHATSAPP_ACCESS_TOKEN,
    "whatsapp_phone_number_id": lambda: config.WHATSAPP_PHONE_NUMBER_ID,
    "whatsapp_app_secret": lambda: config.WHATSAPP_APP_SECRET,
    # X (Twitter)
    "x_bearer_token": lambda: config.X_BEARER_TOKEN,
    "x_api_key": lambda: config.X_API_KEY,
    "x_api_secret": lambda: config.X_API_SECRET,
    "x_access_token": lambda: config.X_ACCESS_TOKEN,
    "x_access_secret": lambda: config.X_ACCESS_SECRET,
    # Meta messaging (Messenger + Instagram Direct share one webhook)
    "messenger_verify_token": lambda: config.MESSENGER_VERIFY_TOKEN,
    "messenger_page_token": lambda: config.MESSENGER_PAGE_TOKEN,
    "instagram_access_token": lambda: config.INSTAGRAM_ACCESS_TOKEN,
    # Search API
    "serpapi_key": lambda: config.SERPAPI_KEY,
    "searxng_url": lambda: config.SEARXNG_URL,
    # Brevo event webhook (delivered/open/bounce callbacks)
    "brevo_webhook_secret": lambda: config.BREVO_WEBHOOK_SECRET,
}


def cred(key: str) -> str:
    """Resolve a credential: DB Setting first, then .env default."""
    from models import Setting
    db_val = Setting.get(key)
    if db_val:
        return db_val
    getter = _ENV_DEFAULTS.get(key)
    return getter() if getter else ""


# Field definitions for the Settings UI: (db_key, label, is_secret)
CHANNEL_FIELDS = {
    "email (Brevo)": [
        ("brevo_smtp_user", "SMTP user (login email)", False),
        ("brevo_smtp_key", "SMTP key", True),
        ("mail_from", "From address (e.g. Name <you@domain.com>)", False),
        ("brevo_webhook_secret", "Webhook secret (for delivery/bounce tracking)", True),
    ],
    "telegram": [
        ("telegram_bot_token", "Bot token (from @BotFather)", True),
        ("telegram_webhook_secret", "Webhook secret (recommended: blocks forged updates)", True),
    ],
    "sms (Twilio)": [
        ("twilio_account_sid", "Account SID (AC...)", False),
        ("twilio_auth_token", "Auth token", True),
        ("twilio_from_number", "From number (e.g. +1555...)", False),
    ],
    "sms (RedSMS)": [
        ("redsms_username", "Username", False),
        ("redsms_password", "Password", True),
        ("redsms_sender_id", "Sender ID", False),
    ],
    "whatsapp (Meta Cloud)": [
        ("whatsapp_access_token", "Access token", True),
        ("whatsapp_phone_number_id", "Phone number ID", False),
        ("whatsapp_app_secret", "App secret (webhook verify)", True),
    ],
    "messenger (FB Page)": [
        ("messenger_page_token", "Page access token", True),
        ("messenger_verify_token", "Webhook verify token (shared with IG)", True),
    ],
    "instagram (Direct)": [
        ("instagram_access_token", "IG access token", True),
    ],
    "x (Twitter)": [
        ("x_bearer_token", "Bearer token (read/monitor)", True),
        ("x_api_key", "API key (consumer key, OAuth1 publish)", False),
        ("x_api_secret", "API secret (consumer secret, OAuth1 publish)", True),
        ("x_access_token", "Access token (user context, OAuth1 publish)", False),
        ("x_access_secret", "Access token secret (OAuth1 publish)", True),
    ],
}
