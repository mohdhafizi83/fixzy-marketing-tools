"""Telegram bot adapter — free, but ONLY to users who have already sent /start.

A Telegram bot cannot initiate a conversation with anyone: that is a hard
platform limit. Telegram identifies users by chat_id (not phone number), so
chat_id is registered when the user sends /start to the bot, which our
/telegram/webhook route receives. A lead is contactable when they have a
telegram_chat_id plus an active consent record.
"""
import requests
from credentials import cred
from adapters import BaseAdapter, SendResult


class TelegramAdapter(BaseAdapter):
    channel = "telegram"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(cred("telegram_bot_token"))

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        chat_id = getattr(lead, "telegram_chat_id", None)
        if not chat_id:
            return SendResult(False, "lead has no telegram_chat_id (user has not sent /start to the bot)")
        if not self.is_configured():
            return SendResult(False, "Telegram bot token not set (Settings -> Channels)")
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{cred('telegram_bot_token')}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=15,
            )
            data = r.json()
            if data.get("ok"):
                return SendResult(True, f"sent to chat {chat_id}")
            return SendResult(False, f"telegram: {data.get('description', r.status_code)}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")
