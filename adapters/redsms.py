"""SMS adapter — RedSMS (Malaysian gateway).

WARNING: this adapter follows the widely circulated RedSMS HTTP GET format,
but the official docs at redsms.com could NOT be reached at build time
(SSL error, Oct 2026). VERIFY the exact parameter names against the
documentation you receive with your RedSMS account before trusting it.
The response codes below assume: positive number = credits remaining,
0 or negative = error. Adjust if their docs differ.

Cost: ~RM0.04-0.09/message on prepaid credit.
"""
import requests
import config
from adapters import BaseAdapter, SendResult


class RedSmsAdapter(BaseAdapter):
    channel = "sms"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(config.REDSMS_USERNAME and config.REDSMS_PASSWORD)

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        if not lead.phone:
            return SendResult(False, "lead has no phone number")
        if not self.is_configured():
            return SendResult(False, "RedSMS credentials not set")
        unsub = lead.unsubscribe_url("sms")
        body = f"{message}\nReply STOP to unsubscribe: {unsub}"
        try:
            r = requests.get(
                "https://www.redsms.com/api/sendsms.php",
                params={
                    "username": config.REDSMS_USERNAME,
                    "password": config.REDSMS_PASSWORD,
                    "mobile": f"+{lead.phone}",
                    "message": body,
                    "sender": config.REDSMS_SENDER_ID or "Fixzy",
                },
                timeout=20,
            )
            text = r.text.strip()
            # Documented convention: numeric response = credits left (success)
            try:
                credits = int(text)
                if credits >= 0:
                    return SendResult(True, f"sent, credits left: {credits}")
                return SendResult(False, f"redsms error code: {credits}")
            except ValueError:
                return SendResult(False, f"unexpected response: {text[:120]}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")
