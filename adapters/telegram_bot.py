"""Telegram bot adapter — RM0, tapi HANYA kepada user yang dah /start bot.

Bot tak boleh mulakan perbualan dengan sesiapa (had platform Telegram).
model: chat_id disimpan sebagai phone dinormalisasi? Tidak — Telegram guna chat_id.
Untuk F1: chat_id didaftarkan melalui /start (webhook/polling ringkas di /telegram/webhook).
Lead dianggap boleh diganggu jika ada telegram_chat_id + consent aktif.
"""
import requests
import config
from adapters import BaseAdapter, SendResult


class TelegramAdapter(BaseAdapter):
    channel = "telegram"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(config.TELEGRAM_BOT_TOKEN)

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        chat_id = getattr(lead, "telegram_chat_id", None)
        if not chat_id:
            return SendResult(False, "lead tiada telegram_chat_id (user belum /start bot)")
        if not self.is_configured():
            return SendResult(False, "TELEGRAM_BOT_TOKEN belum diset")
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=15,
            )
            data = r.json()
            if data.get("ok"):
                return SendResult(True, f"sent to chat {chat_id}")
            return SendResult(False, f"telegram: {data.get('description', r.status_code)}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")
