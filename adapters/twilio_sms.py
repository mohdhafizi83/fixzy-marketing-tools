"""SMS adapter — Twilio (Tier 1, verified against twilio.com/docs, Oct 2026).

Endpoint: POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
Auth: HTTP Basic (Account SID : Auth Token). Form params: To, From, Body.
Malaysia rates ~RM0.04-0.10/message. Trial accounts can only send to
verified numbers — that is a Twilio restriction, not ours.

Message length: Twilio bills per 160-char segment (GSM-7). We do not
auto-trim; long messages simply cost more segments.
"""
import requests
import config
from adapters import BaseAdapter, SendResult


class TwilioSmsAdapter(BaseAdapter):
    channel = "sms"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN
                   and config.TWILIO_FROM_NUMBER)

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        if not lead.phone:
            return SendResult(False, "lead has no phone number")
        if not self.is_configured():
            return SendResult(False, "Twilio credentials not set")
        # Unsubscribe footer is mandatory on every outbound (PDPA)
        unsub = lead.unsubscribe_url("sms")
        body = f"{message}\nReply STOP to unsubscribe: {unsub}"
        try:
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{config.TWILIO_ACCOUNT_SID}/Messages.json",
                auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
                data={"To": f"+{lead.phone}", "From": config.TWILIO_FROM_NUMBER,
                     "Body": body},
                timeout=20,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return SendResult(True, f"queued, sid={data.get('sid', '?')}")
            return SendResult(False, f"twilio {r.status_code}: "
                                   f"{data.get('message', '?')}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")
