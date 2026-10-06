"""Adapter interface — one contract for every channel (brief section 5).

send(lead, message, subject) -> SendResult

Each adapter is self-describing: capability flags stop the UI from showing a
'blast' button for a channel that cannot actually do outbound sends (brief section 6).
"""
from dataclasses import dataclass


@dataclass
class SendResult:
    ok: bool
    detail: str = ""


class BaseAdapter:
    channel: str = "base"
    supports_outbound: bool = False       # can this channel blast automatically?
    requires_consent: bool = True         # PDPA: an active consent record is required
    needs_credential: bool = True

    def is_configured(self) -> bool:
        raise NotImplementedError

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        raise NotImplementedError


def get_adapter(channel: str) -> BaseAdapter:
    if channel == "email":
        from adapters.brevo_email import BrevoEmailAdapter
        return BrevoEmailAdapter()
    if channel == "telegram":
        from adapters.telegram_bot import TelegramAdapter
        return TelegramAdapter()
    if channel == "sms":
        # Prefer Twilio when configured; fall back to RedSMS
        from adapters.twilio_sms import TwilioSmsAdapter
        from adapters.redsms import RedSmsAdapter
        tw = TwilioSmsAdapter()
        return tw if tw.is_configured() else RedSmsAdapter()
    if channel == "whatsapp":
        from adapters.whatsapp_cloud import WhatsAppAdapter
        return WhatsAppAdapter()
    if channel == "x":
        from adapters.x_api import XAdapter
        return XAdapter()
    raise ValueError(f"Unknown channel: {channel}")
