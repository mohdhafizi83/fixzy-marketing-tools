"""Adapter interface — satu kontrak untuk semua channel (brief §5).

send(lead, message, channel) → SendResult
Setiap adapter self-describing: capability flags supaya UI tak tunjuk
'blast button' untuk channel yang tak sokong outbound (brief §6).
"""
from dataclasses import dataclass


@dataclass
class SendResult:
    ok: bool
    detail: str = ""


class BaseAdapter:
    channel: str = "base"
    supports_outbound: bool = False       # boleh blast automatik?
    requires_consent: bool = True         # PDPA: perlu rekod consent aktif
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
    raise ValueError(f"Channel tak dikenali: {channel}")
