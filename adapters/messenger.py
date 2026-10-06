"""Messenger (FB Page) + Instagram Direct adapter — TIER 2: REPLY-ONLY.

Verified vs developers.facebook.com (Meta for Developers, Oct 2026):
  - Webhooks: same hub.challenge handshake as WhatsApp. Inbound messages
    arrive under entry[].messaging[] — object "page" for Messenger,
    object "instagram" for Instagram Direct. Both share this structure.
  - Send API (shared by both products; version from config.GRAPH_API_VERSION):
      POST https://graph.facebook.com/{VERSION}/me/messages
      body: {"recipient": {"id": <PSID>},
             "messaging_type": "RESPONSE",
             "message": {"text": "..."}}
    Auth: Page access token (Messenger) / IG-connected access token.
  - 24-hour rule: free-form text is deliverable only within 24h of the
    user messaging the Page/IG account first. Cold outreach has no
    supported API — do not add a blast path.

Like the WhatsApp adapter, send() REFUSES blasts by design; only
send_reply() works, and only inside the window.
"""
import requests
import config
from credentials import cred
from adapters import BaseAdapter, SendResult

GRAPH = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"


class _MetaMessagingBase(BaseAdapter):
    """Shared Send API logic for Messenger and Instagram Direct."""
    supports_outbound = False   # reply-only: no blind blasts
    reply_only = True
    token_key = ""              # which credential holds the send token

    def is_configured(self) -> bool:
        return bool(cred(self.token_key))

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        return SendResult(False,
            f"{self.channel} is reply-only (24h window). Use send_reply() "
            "from the Inbox — cold outreach has no supported API.")

    def send_reply(self, recipient_id: str, text: str) -> SendResult:
        """Free-form reply. Only works if the user messaged us < 24h ago."""
        if not recipient_id:
            return SendResult(False, "no recipient id for this conversation")
        if not self.is_configured():
            return SendResult(False,
                f"{self.channel} access token not set (Settings -> Channels)")
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }
        try:
            r = requests.post(
                f"{GRAPH}/me/messages",
                json=payload,
                headers={"Authorization": f"Bearer {cred(self.token_key)}"},
                timeout=20,
            )
            data = r.json()
            if r.status_code in (200, 201) and not data.get("error"):
                return SendResult(True,
                    f"queued, mid={data.get('message_id', '?')}")
            err = data.get("error", {})
            return SendResult(False, f"{self.channel} {r.status_code}: "
                                   f"{err.get('message', '?')}")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")


class MessengerAdapter(_MetaMessagingBase):
    channel = "messenger"
    token_key = "messenger_page_token"


class InstagramAdapter(_MetaMessagingBase):
    channel = "instagram"
    token_key = "instagram_access_token"
