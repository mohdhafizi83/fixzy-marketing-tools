"""Crawler — replaces the legacy HtmlAgilityPack. requests + selectolax.

F1 sources: text files, URL lists, pasted text, full-site crawl (follows <a href>).
Polite crawling: delay between requests, respects robots.txt, depth and page caps.
"""
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from selectolax.lexbor import LexborHTMLParser

UA = "FixzyMarketingTools/0.1 (lead extraction; contact admin via site)"
DEFAULT_DELAY_S = 1.0
DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_DEPTH = 2


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
            except Exception:
                rp = None  # robots.txt unreadable -> assume allowed (same as legacy)
            self._robots[host] = rp
        if rp is None:
            return True
        return rp.can_fetch(UA, url)

    def fetch(self, url: str) -> str:
        """Fetch the HTML for one URL. Returns '' on failure or block."""
        if not self._allowed(url):
            return ""
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code >= 400:
                return ""
            return r.text
        except requests.RequestException:
            return ""

    def crawl_site(self, start_url: str,
                  on_page=None) -> tuple[list[str], list[str]]:
        """Breadth-first crawl over <a href> links within the same domain.

        on_page(url, n_emails, n_phones) is called per page — for progress UI.
        Returns (emails, phones), unique across all pages.
        """
        from extractor import extract_emails, extract_phones_my

        start_url = urldefrag(start_url).url
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
