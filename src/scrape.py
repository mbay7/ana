"""Fetch a web page and extract readable text for onboarding.

Stdlib HTML parsing plus `requests` (a transitive dependency of Streamlit), so
no new package is required to let a client point the assistant at their own site.
"""
import re
from html.parser import HTMLParser

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


def fetch_text(url: str, timeout: int = 15) -> str:
    """Return clean page text for a URL, or '' if it cannot be read."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(
            url, timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) assistant-onboarding/1.0"},
        )
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