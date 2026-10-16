"""Fetch a web page and extract readable text for onboarding.

Stdlib HTML parsing plus `urllib3` and `certifi` (installed with `requests`,
which Streamlit needs), so no new package is required to let a client point the assistant at their own site.
"""
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import certifi
import urllib3


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
_MAX_BYTES = 5_000_000
_UA = "Mozilla/5.0 (X11; Linux x86_64) assistant-onboarding/1.0"


def _ip_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip.split("%", 1)[0])
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    # Only public internet addresses: no private (10/8, 172.16/12, 192.168/16, fc00::/7),
    # loopback (127/8, ::1), link-local or cloud metadata (169.254/16, fe80::/10),
    # shared, multicast, reserved or unspecified addresses.
    return not addr.is_global or addr.is_multicast


def resolve_public(url: str):
    """Resolve an http(s) URL's host ONCE and return (parts, ip) if every address is public.

    Returns None when the scheme is not http(s), the host cannot be resolved, or
    any address it resolves to is not public. The caller connects to the returned
    ip, so a second DNS lookup (DNS rebinding) cannot swap in a private address.
    """
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    try:
        infos = socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError, UnicodeError):
        return None
    if not infos:
        return None
    try:
        ips = [info[4][0] for info in infos]
        if any(_ip_blocked(ip) for ip in ips):
            return None
    except ValueError:
        return None
    return parts, ips[0]


def url_allowed(url: str) -> bool:
    """True only for an http(s) URL whose host resolves solely to public addresses."""
    return resolve_public(url) is not None


def _fetch_pinned(parts, ip, timeout):
    """GET the URL by connecting to the already-checked `ip`, never resolving the name again.

    The Host header and the TLS name (SNI and certificate check) still use the
    real host name, so HTTPS works and is verified as normal.
    Returns (status, headers, text).
    """
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = (parts.path or "/") + (("?" + parts.query) if parts.query else "")
    host_header = host if parts.port is None else f"{host}:{parts.port}"
    to = urllib3.Timeout(connect=timeout, read=timeout)
    if parts.scheme == "https":
        pool = urllib3.HTTPSConnectionPool(
            ip, port, timeout=to, retries=False, cert_reqs="CERT_REQUIRED",
            ca_certs=certifi.where(), assert_hostname=host, server_hostname=host,
        )
    else:
        pool = urllib3.HTTPConnectionPool(ip, port, timeout=to, retries=False)
    try:
        r = pool.urlopen(
            "GET", path, headers={"Host": host_header, "User-Agent": _UA},
            redirect=False, preload_content=False,
        )
        body = r.read(_MAX_BYTES + 1, decode_content=True)
        r.release_conn()
    finally:
        pool.close()
    if len(body) > _MAX_BYTES:
        body = body[:_MAX_BYTES]
    headers = {k.lower(): v for k, v in r.headers.items()}
    charset = None
    m = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
    if m:
        charset = m.group(1)
    try:
        text = body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")
    return r.status, headers, text


def fetch_text(url: str, timeout: int = 15) -> str:
    """Return clean page text for a URL, or '' if it cannot be read or is not allowed.

    Only public http(s) sites are fetched. Each hop resolves the host once, checks
    every address, then connects to that checked address. Redirects are followed
    by hand (at most five), each one checked the same way.
    """
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    for _ in range(_MAX_REDIRECTS + 1):
        checked = resolve_public(url)
        if checked is None:
            return ""
        parts, ip = checked
        try:
            status, headers, html = _fetch_pinned(parts, ip, timeout)
        except Exception:
            return ""
        if status in (301, 302, 303, 307, 308):
            nxt = headers.get("location")
            if not nxt:
                return ""
            url = urljoin(url, nxt)
            continue
        break
    else:
        return ""
    if not 200 <= status < 300:
        return ""
    ctype = headers.get("content-type", "").lower()
    if "html" not in ctype and "</html>" not in html[:2000].lower():
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    text = re.sub(r"\n{2,}", "\n\n", "\n".join(parser.parts))
    return text.strip()
