"""Email adapter — Brevo SMTP relay.

Docs rasmi (help.brevo.com + developers.brevo.com/docs/smtp-integration):
  host: smtp-relay.brevo.com, port 587 (STARTTLS), user = SMTP login email,
  password = SMTP key. Free tier: 300 mesej/hari.
"""
import asyncio
import aiosmtplib
import config
from adapters import BaseAdapter, SendResult


class BrevoEmailAdapter(BaseAdapter):
    channel = "email"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(config.BREVO_SMTP_USER and config.BREVO_SMTP_KEY and config.MAIL_FROM)

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        if not lead.email:
            return SendResult(False, "lead tiada email")
        msg = self._build(lead, message, subject)
        try:
            asyncio.run(self._send_async(msg))
            return SendResult(True, f"delivered via {config.BREVO_SMTP_HOST}")
        except aiosmtplib.SMTPException as e:
            return SendResult(False, f"SMTP error: {e}")
        except OSError as e:
            return SendResult(False, f"network: {e}")

    def _build(self, lead, message: str, subject: str | None):
        from email.message import EmailMessage
        m = EmailMessage()
        m["From"] = config.MAIL_FROM
        m["To"] = lead.email
        m["Subject"] = subject or "Mesej dari Fixzy Marketing Tools"
        # Unsubscribe link wajib dalam setiap outbound (PDPA)
        unsub = lead.unsubscribe_url("email")
        m["List-Unsubscribe"] = f"<{unsub}>"
        body = message + f"\n\n---\nTak mahu mesej sebegini lagi? Berhenti melanggan: {unsub}\n"
        m.set_content(body)
        return m

    async def _send_async(self, msg):
        await aiosmtplib.send(
            msg,
            hostname=config.BREVO_SMTP_HOST,
            port=config.BREVO_SMTP_PORT,
            username=config.BREVO_SMTP_USER,
            password=config.BREVO_SMTP_KEY,
            start_tls=True,
            timeout=30,
        )
