"""X (Twitter) adapter — TIER 3: PUBLISH + MONITOR, no cold DMs.

Verified vs docs.x.com (Oct 2026):
  - Publish: POST https://api.x.com/2/tweets (OAuth1 user context)
  - Monitor: GET https://api.x.com/2/tweets/search/recent (bearer token)
  - Pay-per-use pricing (~$0.005/post read per brief, per X pricing page)

DMing strangers is NOT available on any affordable X tier — do not add it.
"""
import requests
from credentials import cred
from adapters import BaseAdapter, SendResult


class XAdapter(BaseAdapter):
    channel = "x"
    # Publishing is outbound but NOT lead-targeted blast; keep blast flag off.
    supports_outbound = False
    publish = True

    def is_configured(self) -> bool:
        return bool(cred("x_bearer_token"))

    def can_publish(self) -> bool:
        return bool(cred("x_api_key") and cred("x_api_secret"))

    def send(self, lead, message: str, subject: str | None = None) -> SendResult:
        return SendResult(False,
            "X is publish/monitor only — no per-lead sending by design.")

    def publish_post(self, text: str) -> SendResult:
        """Post a public tweet. Requires OAuth1 credentials."""
        if not self.can_publish():
            return SendResult(False, "X OAuth1 credentials not set")
        # OAuth1 signing via requests-oauthlib if installed; else manual note
        try:
            from requests_oauthlib import OAuth1
            auth = OAuth1(cred("x_api_key"), cred("x_api_secret"))
            r = requests.post("https://api.x.com/2/tweets",
                             json={"text": text}, auth=auth, timeout=20)
            data = r.json()
            if r.status_code in (200, 201):
                return SendResult(True, f"posted, id={data.get('data', {}).get('id', '?')}")
            return SendResult(False, f"x {r.status_code}: {data.get('detail', '?')}")
        except ImportError:
            return SendResult(False, "requests-oauthlib not installed "
                                    "(pip install requests-oauthlib)")
        except requests.RequestException as e:
            return SendResult(False, f"network: {e}")

    def search_recent(self, query: str, max_results: int = 20) -> tuple[list[dict], str]:
        """Recent public posts matching a query — for lead/brand monitoring."""
        if not self.is_configured():
            return [], "X bearer token not set (Settings -> Channels)"
        try:
            r = requests.get(
                "https://api.x.com/2/tweets/search/recent",
                params={"query": query, "max_results": max(10, min(100, max_results))},
                headers={"Authorization": f"Bearer {cred('x_bearer_token')}"},
                timeout=20,
            )
            data = r.json()
            if "data" in data:
                posts = [{"id": t["id"], "text": t["text"]} for t in data["data"]]
                return posts, ""
            return [], f"x search: {data.get('detail', 'no data')}"
        except requests.RequestException as e:
            return [], f"network: {e}"
