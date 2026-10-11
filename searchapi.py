"""Search API for lead source discovery (F2).

Replaces the dead Google <cite> scraping from the legacy app. Two backends:
  - SerpAPI (serpapi.com, ~$0.0008/search, 250 free/month)
  - SearXNG (self-hosted, free, no key)

Credential resolution order: DB Setting (editable in Settings UI) first,
then .env as fallback. Returns result URLs; feed them to the crawler to
extract contacts.
"""
import requests

import config
from netguard import check_url_allowed


def active_backend() -> str:
    """Which backend is configured: 'serpapi', 'searxng', or 'none'."""
    from models import Setting
    if Setting.get("serpapi_key") or config.SERPAPI_KEY:
        return "serpapi"
    if Setting.get("searxng_url") or config.SEARXNG_URL:
        return "searxng"
    return "none"


def search(query: str, num: int = 10) -> tuple[list[str], str]:
    """Return (urls, error). Tries SerpAPI first, then SearXNG."""
    backend = active_backend()
    if backend == "serpapi":
        return _serpapi(query, num)
    if backend == "searxng":
        return _searxng(query, num)
    return [], "No search API configured. Add a SerpAPI key or SearXNG URL in Settings."


def _serpapi(query: str, num: int) -> tuple[list[str], str]:
    from models import Setting
    key = Setting.get("serpapi_key") or config.SERPAPI_KEY
    try:
        r = requests.get("https://serpapi.com/search.json",
                        params={"q": query, "api_key": key,
                               "num": num, "engine": "google"},
                        timeout=20)
        data = r.json()
        if "error" in data:
            return [], f"serpapi: {data['error']}"
        urls = [res["link"] for res in data.get("organic_results", [])
                if res.get("link")]
        return urls, ""
    except requests.RequestException as e:
        return [], f"serpapi network: {e}"
    except ValueError:
        return [], "serpapi: unexpected response"


def _searxng(query: str, num: int) -> tuple[list[str], str]:
    from models import Setting
    base = (Setting.get("searxng_url") or config.SEARXNG_URL).rstrip("/")
    # Defense in depth: the URL is user-configurable (Settings UI / .env) —
    # refuse private/internal targets even if a bad value was saved earlier.
    ok, reason = check_url_allowed(base,
                                   allow_private=config.ALLOW_PRIVATE_LLM)
    if not ok:
        return [], f"searxng blocked: {reason}"
    try:
        r = requests.get(f"{base}/search",
                         params={"q": query, "format": "json", "pageno": 1},
                         timeout=20, allow_redirects=False)
        if r.is_redirect:
            # A redirect could point at an internal host: refuse, don't follow.
            return [], "searxng blocked: redirect refused"
        results = r.json().get("results", [])
        urls = [res["url"] for res in results[:num] if res.get("url")]
        return urls, ""
    except requests.RequestException as e:
        return [], f"searxng network: {e}"
    except ValueError:
        return [], "searxng: unexpected response (is format=json enabled?)"
