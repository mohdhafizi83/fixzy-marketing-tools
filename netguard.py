"""SSRF guard for every user-configurable outbound URL.

Shared policy used by the crawler (CRAWL_ALLOW_PRIVATE), the SearXNG search
backend (searchapi.py) and LLM providers (aicopy.py / Settings -> LLM):

  * scheme must be http or https (no file://, gopher://, ...)
  * no userinfo in the URL (http://user:***@host/ is rejected outright)
  * the host is resolved with socket.getaddrinfo and every returned address
    is checked with ipaddress: loopback, RFC1918/private, CGNAT, link-local
    (this includes the cloud metadata IP 169.254.169.254), multicast and
    reserved ranges are refused
  * DNS failure is treated as private (fail closed — an unresolvable name is
    never fetched blindly)

Callers may pass allow_private=True for a deliberate local endpoint:
LLM providers honour ALLOW_PRIVATE_LLM=1 (documented escape hatch for a
local Ollama/llama.cpp server), the crawler honours CRAWL_ALLOW_PRIVATE=1.
Default is deny. Outbound calls made through this guard must also use
allow_redirects=False — a public host 302-ing to 169.254.169.254 would
otherwise bypass the check.
"""
import ipaddress
import socket
from urllib.parse import urlparse


def is_private_host(host: str) -> bool:
    """True if host is an IP literal or resolves to a private/reserved address.

    DNS failures return True (fail closed).
    """
    if not host:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return True
    return False


def check_url_allowed(url: str, allow_private: bool = False) -> tuple[bool, str]:
    """Return (allowed, reason). Empty reason means allowed.

    allow_private=True skips the private-range check but still enforces the
    scheme and userinfo rules.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "only http/https URLs are allowed"
    if parsed.username or parsed.password:
        return False, "URLs with embedded credentials (user:***@host) are not allowed"
    host = parsed.hostname or ""
    if not host:
        return False, "URL has no host"
    if allow_private:
        return True, ""
    if not is_private_host(host):
        return True, ""
    return False, (f"target '{host}' is a private/internal address — blocked "
                   "(SSRF protection). For a local LLM server set "
                   "ALLOW_PRIVATE_LLM=1 in .env; for internal crawl targets "
                   "set CRAWL_ALLOW_PRIVATE=1. Only do this for hosts you own.")
