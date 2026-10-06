"""Konfigurasi pusat — semua secrets dari .env, tiada hardcode."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
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

# Link unsubscribe perlu domain public supaya boleh diklik penerima
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5558")

# Rate cap per channel per jam (Brevo free = 300/hr; override ikut akaun anda)
RATE_LIMITS_PER_HOUR = {
    "email": int(os.getenv("EMAIL_RATE_PER_HOUR", "300")),
    "telegram": int(os.getenv("TELEGRAM_RATE_PER_HOUR", "25")),  # Telegram ~30/s global; kita konservatif
}

# AI copy drafts (local LLM, F1 optional hook)
LLM_URL = os.getenv("LLM_URL", "http://localhost:8080")
