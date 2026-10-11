"""Crawler — replaces the legacy HtmlAgilityPack. requests + selectolax.

F1 sources: text files, URL lists, pasted text, full-site crawl (follows <a href>).
Polite crawling: delay between requests, respects robots.txt, depth and page caps.

Security: SSRF guard — targets resolving to loopback/private/link-local/reserved
addresses (cloud metadata endpoints like 169.254.169.254, internal LAN
services) are refused unless CRAWL_ALLOW_PRIVATE=1 is set explicitly.
"""
import time
import urllib.robotparser
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from selectolax.lexbor import LexborHTMLParser

from netguard import check_url_allowed

UA = "FixzyMarketingTools/0.1 (lead extraction; contact admin via site)"
DEFAULT_DELAY_S = 1.0
DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_DEPTH = 2
MAX_PAGE_BYTES = 2 * 1024 * 1024  # 2 MB per page cap


def check_target_allowed(url: str) -> tuple[bool, str]:
    """Public guard used before any crawl/fetch of a user-supplied URL.

    Delegates to netguard (scheme + userinfo + resolved-IP policy); private
    targets are allowed only when CRAWL_ALLOW_PRIVATE is set explicitly.
    """
    import config
    return check_url_allowed(url, allow_private=config.CRAWL_ALLOW_PRIVATE)


class Crawler:
    def __init__(self, delay_s: float = DEFAULT_DELAY_S,
                 max_pages: int = DEFAULT_MAX_PAGES,
                 max_depth: int = DEFAULT_MAX_DEPTH):
        self.delay_s = delay_s
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
                rp.read()
            except (OSError, ValueError):
                rp = None  # robots.txt unreadable -> assume allowed (same as legacy)
            self._robots[host] = rp
        if rp is None:
            return True
        return rp.can_fetch(UA, url)

    def fetch(self, url: str) -> str:
        """Fetch the HTML for one URL. Returns '' on failure or block.

        Redirects are NOT followed blindly: each 3xx Location is re-checked
        with the SSRF guard (up to 3 hops), so a public host cannot bounce
        the crawler into 169.254.169.254 or an internal LAN address.
        """
        if not self._allowed(url):
            return ""
        for _hop in range(4):
            try:
                # stream=True + explicit byte cap: never buffer an unbounded
                # body (a hostile or misconfigured site could exhaust memory).
                with self.session.get(url, timeout=15, stream=True,
                                      allow_redirects=False) as r:
                    if r.is_redirect:
                        loc = r.headers.get("Location", "")
                        if not loc:
                            return ""
                        url = urldefrag(urljoin(url, loc)).url
                        allowed, _reason = check_target_allowed(url)
                        if not allowed:
                            return ""
                        if not self._allowed(url):
                            return ""
                        continue
                    if r.status_code >= 400:
                        return ""
                    chunks, size = [], 0
                    for chunk in r.iter_content(chunk_size=65536):
                        chunks.append(chunk)
                        size += len(chunk)
                        if size > MAX_PAGE_BYTES:
                            break
                    return b"".join(chunks).decode(r.encoding or "utf-8",
                                                   errors="replace")
            except requests.RequestException:
                return ""
        return ""  # redirect chain too long

    def crawl_site(self, start_url: str,
                  on_page=None) -> tuple[list[str], list[str]]:
        """Breadth-first crawl over <a href> links within the same domain.

        on_page(url, n_emails, n_phones) is called per page — for progress UI.
        Returns (emails, phones), unique across all pages.
        """
        from extractor import extract_emails, extract_phones_my

        start_url = urldefrag(start_url).url
        allowed, reason = check_target_allowed(start_url)
        if not allowed:
            raise ValueError(reason)
        root_host = urlparse(start_url).netloc
        queue: list[tuple[str, int]] = [(start_url, 0)]
        visited: set[str] = set()
        emails: set[str] = set()
        phones: set[str] = set()
        pages = 0

        while queue and pages < self.max_pages:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            html = self.fetch(url)
            if not html:
                continue
            pages += 1
            page_emails = extract_emails(html)
            page_phones = extract_phones_my(html)
            emails.update(page_emails)
            phones.update(page_phones)
            if on_page:
                on_page(url, len(page_emails), len(page_phones))

            if depth < self.max_depth:
                parser = LexborHTMLParser(html)
                for a in parser.css("a[href]"):
                    href = a.attributes.get("href") or ""
                    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                        continue
                    absu = urldefrag(urljoin(url, href)).url
                    if urlparse(absu).netloc == root_host and absu not in visited:
                        queue.append((absu, depth + 1))
            if queue:
                time.sleep(self.delay_s)
        return sorted(emails), sorted(phones)
