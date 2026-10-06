"""WhatsApp Cloud API adapter (Meta) — TIER 2: REPLY-ONLY.

Verified vs developers.facebook.com (Oct 2026; API version from
config.GRAPH_API_VERSION, currently v24.0 — available until Feb 2028):
  POST https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages
  Free-form text messages are ONLY deliverable within the 24-hour customer
  service window that opens when the USER messages us first.
  Outside that window, only pre-approved TEMPLATE messages work, and
  marketing templates are billed (~RM0.50/message MY since Jul 2025).

This adapter therefore REFUSES free-form blasts. It only sends:
  - reply text when a conversation window is open (lead.whatsapp_window_open),
  - template messages when explicitly requested with a template name.

Cold-blasting WhatsApp = number banned. The capability flags below make the
UI honest about this: whatsapp is NOT a blast channel.
"""
import requests
import config
from credentials import cred
from adapters import BaseAdapter, SendResult

GRAPH = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"


class WhatsAppAdapter(BaseAdapter):
    channel = "whatsapp"
    # Deliberately False: no blind blasts. Reply-only channel.
    supports_outbound = False
    reply_only = True

    def is_configured(self) -> bool:
        return bool(cred("whatsapp_access_token") and cred("whatsapp_phone_number_id"))

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        return SendResult(False,
            "WhatsApp is reply-only (24h window). Use send_reply() or "
            "send_template() explicitly — blind blasts are blocked by design.")

    def send_reply(self, lead, text: str) -> SendResult:
        """Free-form reply. Only works if the user messaged us < 24h ago."""
        wa_id = getattr(lead, "whatsapp_number", None) or lead.phone
        if not wa_id:
            return SendResult(False, "lead has no WhatsApp number")
        if not self.is_configured():
            return SendResult(False, "WhatsApp credentials not set")
        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"body": text},
        }
        return self._post(payload)

    def send_template(self, lead, template_name: str,
                     components: list | None = None) -> SendResult:
        """Approved template message — works outside the 24h window, billed."""
        wa_id = getattr(lead, "whatsapp_number", None) or lead.phone
        if not wa_id:
            return SendResult(False, "lead has no WhatsApp number")
        if not self.is_configured():
            return SendResult(False, "WhatsApp credentials not set")
        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
            },
        }
        if components:
            payload["template"]["components"] = components
        return self._post(payload)

    def _post(self, payload) -> SendResult:
        try:
            r = requests.post(
                f"{GRAPH}/{cred('whatsapp_phone_number_id')}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {cred('whatsapp_access_token')}"},
                timeout=20,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return SendResult(True, f"queued, wid={data.get('messages', [{}])[0].get('id', '?')}")
            err = data.get("error", {})
            return SendResult(False, f"whatsapp {r.status_code}: "
                                   f"{err.get('message', '?')}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")
