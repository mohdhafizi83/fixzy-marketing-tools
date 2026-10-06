"""Search API for lead source discovery (F2).

Replaces the dead Google <cite> scraping from the legacy app. Two backends:
  - SerpAPI (serpapi.com, ~$0.0008/search, 250 free/month)
  - SearXNG (self-hosted, free, no key)

Returns result URLs; feed them to the crawler to extract contacts.
"""
import requests
import config


def search(query: str, num: int = 10) -> tuple[list[str], str]:
    """Return (urls, error). Tries SerpAPI first, then SearXNG."""
    if config.SERPAPI_KEY:
        urls, err = _serpapi(query, num)
        if urls:
            return urls, ""
        return [], err
    if config.SEARXNG_URL:
        return _searxng(query, num)
    return [], "No search API configured (set SERPAPI_KEY or SEARXNG_URL in .env)"


def _serpapi(query: str, num: int) -> tuple[list[str], str]:
    try:
        r = requests.get("https://serpapi.com/search.json",
                        params={"q": query, "api_key": config.SERPAPI_KEY,
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
    base = config.SEARXNG_URL.rstrip("/")
    try:
        r = requests.get(f"{base}/search",
                        params={"q": query, "format": "json", "pageno": 1},
                        timeout=20)
        results = r.json().get("results", [])
        urls = [res["url"] for res in results[:num] if res.get("url")]
        return urls, ""
    except requests.RequestException as e:
        return [], f"searxng network: {e}"
    except ValueError:
        return [], "searxng: unexpected response (is format=json enabled?)"
