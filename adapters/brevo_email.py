"""Email adapter — Brevo SMTP relay.

Official docs (help.brevo.com and developers.brevo.com/docs/smtp-integration):
  host: smtp-relay.brevo.com, port 587 (STARTTLS), user = SMTP login email,
  password = SMTP key. Free tier: 300 messages/day.
"""
import asyncio

import aiosmtplib

from adapters import BaseAdapter, SendResult
from credentials import cred


class BrevoEmailAdapter(BaseAdapter):
    channel = "email"
    supports_outbound = True

    def is_configured(self) -> bool:
        return bool(cred("brevo_smtp_user") and cred("brevo_smtp_key")
                   and cred("mail_from"))

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        if not lead.email:
            return SendResult(False, "lead has no email address")
        msg = self._build(lead, message, subject)
        try:
            asyncio.run(self._send_async(msg))
            return SendResult(True, "delivered via Brevo SMTP relay")
        except aiosmtplib.SMTPException as e:
            return SendResult(False, f"SMTP error: {e}")
        except OSError as e:
            return SendResult(False, f"network: {e}")

    def _build(self, lead, message: str, subject: str | None):
        from email.message import EmailMessage
        m = EmailMessage()
        m["From"] = cred("mail_from")
        m["To"] = lead.email
        m["Subject"] = subject or "Message from Fixzy Marketing Tools"
        # An unsubscribe link is mandatory in every outbound message (PDPA)
        unsub = lead.unsubscribe_url("email")
        m["List-Unsubscribe"] = f"<{unsub}>"
        body = message + f"\n\n---\nDon't want these messages anymore? Unsubscribe: {unsub}\n"
        m.set_content(body)
        return m

    async def _send_async(self, msg):
        await aiosmtplib.send(
            msg,
            hostname="smtp-relay.brevo.com",
            port=587,
            username=cred("brevo_smtp_user"),
            password=cred("brevo_smtp_key"),
            start_tls=True,
            timeout=30,
        )
