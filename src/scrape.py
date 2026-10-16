"""Fetch a web page and extract readable text for onboarding.

Stdlib HTML parsing plus `requests` (a transitive dependency of Streamlit), so
no new package is required to let a client point the assistant at their own site.
"""
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import requests

_SKIP = {"script", "style", "noscript", "head", "nav", "header", "footer",
         "aside", "form", "select", "option", "svg", "button"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in _SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in _SKIP and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.parts.append(text)


_MAX_REDIRECTS = 5


def _ip_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip.split("%", 1)[0])
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    # Only public internet addresses: no private (10/8, 172.16/12, 192.168/16, fc00::/7),
    # loopback (127/8, ::1), link-local or cloud metadata (169.254/16, fe80::/10),
    # shared, multicast, reserved or unspecified addresses.
    return not addr.is_global or addr.is_multicast


def url_allowed(url: str) -> bool:
    """True only for an http(s) URL whose host resolves solely to public addresses."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
        infos = socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError, UnicodeError):
        return False
    if not infos:
        return False
    try:
        return not any(_ip_blocked(info[4][0]) for info in infos)
    except ValueError:
        return False


def fetch_text(url: str, timeout: int = 15) -> str:
    """Return clean page text for a URL, or '' if it cannot be read or is not allowed.

    Only public http(s) sites are fetched: addresses inside the server's own
    network (and the cloud metadata address) are refused, including after redirects.
    """
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    try:
        for _ in range(_MAX_REDIRECTS + 1):
            if not url_allowed(url):
                return ""
            resp = requests.get(
                url, timeout=timeout, allow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) assistant-onboarding/1.0"},
            )
            if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                nxt = resp.headers.get("location")
                if not nxt:
                    return ""
                url = urljoin(url, nxt)
                continue
            break
        else:
            return ""
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    resp.encoding = resp.apparent_encoding
    html = resp.text
    ctype = resp.headers.get("content-type", "").lower()
    if "html" not in ctype and "</html>" not in html[:2000].lower():
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    text = re.sub(r"\n{2,}", "\n\n", "\n".join(parser.parts))
    return text.strip()
