"""Owner pages need a password; the page fetcher only reaches public sites."""
import socket

import pytest

from src import admin, scrape


def test_admin_off_without_password():
    assert not admin.admin_available({"ANA_ADMIN": "1"})
    assert not admin.password_ok("anything", {"ANA_ADMIN": "1", "ANA_ADMIN_PASSWORD": ""})


def test_admin_off_without_switch():
    env = {"ANA_ADMIN_PASSWORD": "s3cret-test"}
    assert not admin.admin_available(env)
    assert not admin.password_ok("s3cret-test", env)


def test_admin_password_checked():
    env = {"ANA_ADMIN": "yes", "ANA_ADMIN_PASSWORD": "s3cret-test"}
    assert admin.admin_available(env)
    assert admin.password_ok("s3cret-test", env)
    assert not admin.password_ok("s3cret-tesT", env)
    assert not admin.password_ok("", env)
    assert not admin.password_ok(None, env)


def _resolve_to(monkeypatch, ip):
    fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
    monkeypatch.setattr(scrape.socket, "getaddrinfo", lambda *a, **k: [(fam, socket.SOCK_STREAM, 6, "", (ip, 443))])


@pytest.mark.parametrize("ip", [
    "10.0.0.5", "172.16.3.4", "192.168.1.1", "127.0.0.1", "127.8.8.8",
    "169.254.169.254", "0.0.0.0", "::1", "fc00::1", "fd12:3456::1", "fe80::1", "::ffff:127.0.0.1",
    "100.64.0.1",
])
def test_private_and_metadata_addresses_blocked(monkeypatch, ip):
    _resolve_to(monkeypatch, ip)
    assert not scrape.url_allowed("https://looks-public.example/")
    called = []
    monkeypatch.setattr(scrape.requests, "get", lambda *a, **k: called.append(1))
    assert scrape.fetch_text("https://looks-public.example/") == ""
    assert not called  # refused before any request is made


def test_public_address_allowed(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    assert scrape.url_allowed("https://shop.example.com/about")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://example.com", "http://"])
def test_non_web_schemes_blocked(url):
    assert not scrape.url_allowed(url)
    assert scrape.fetch_text(url) == ""


def test_any_private_address_in_dns_answer_blocks(monkeypatch):
    monkeypatch.setattr(scrape.socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
    ])
    assert not scrape.url_allowed("https://mixed.example/")


class _Resp:
    def __init__(self, status, location=None, text="<html><body><p>Hello</p></body></html>"):
        self.status_code = status
        self.is_redirect = status in (301, 302, 303, 307, 308)
        self.headers = {"location": location} if location else {"content-type": "text/html"}
        self.text = text
        self.apparent_encoding = "utf-8"
        self.encoding = None

    def raise_for_status(self):
        pass


def test_redirect_to_private_address_blocked(monkeypatch):
    def resolve(host, *a, **k):
        ip = "169.254.169.254" if host == "metadata.internal" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

    monkeypatch.setattr(scrape.socket, "getaddrinfo", resolve)
    urls = []

    def fake_get(url, **k):
        urls.append(url)
        assert k.get("allow_redirects") is False
        return _Resp(302, "http://metadata.internal/latest/meta-data/")

    monkeypatch.setattr(scrape.requests, "get", fake_get)
    assert scrape.fetch_text("https://shop.example.com/") == ""
    assert urls == ["https://shop.example.com/"]


def test_public_page_text_extracted(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    monkeypatch.setattr(scrape.requests, "get", lambda url, **k: _Resp(200))
    assert scrape.fetch_text("shop.example.com") == "Hello"
