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
    monkeypatch.setattr(scrape, "_fetch_pinned", lambda *a, **k: called.append(1))
    assert scrape.fetch_text("https://looks-public.example/") == ""
    assert not called  # refused before any connection is made


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


PAGE = "<html><body><p>Hello</p></body></html>"


def test_connects_to_the_checked_address_not_a_second_lookup(monkeypatch):
    # DNS rebinding: first answer public, any later answer private. Only one
    # lookup may happen per hop, and the connection must use that checked address.
    answers = iter(["93.184.216.34", "127.0.0.1", "127.0.0.1"])
    lookups = []

    def resolve(host, *a, **k):
        ip = next(answers)
        lookups.append(ip)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]

    monkeypatch.setattr(scrape.socket, "getaddrinfo", resolve)
    used = []

    def fake_fetch(parts, ip, timeout):
        used.append((parts.hostname, ip))
        return 200, {"content-type": "text/html"}, PAGE

    monkeypatch.setattr(scrape, "_fetch_pinned", fake_fetch)
    assert scrape.fetch_text("https://shop.example.com/") == "Hello"
    assert lookups == ["93.184.216.34"]
    assert used == [("shop.example.com", "93.184.216.34")]


def test_redirect_to_private_address_blocked(monkeypatch):
    def resolve(host, *a, **k):
        ip = "169.254.169.254" if host == "metadata.internal" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

    monkeypatch.setattr(scrape.socket, "getaddrinfo", resolve)
    used = []

    def fake_fetch(parts, ip, timeout):
        used.append(ip)
        return 302, {"location": "http://metadata.internal/latest/meta-data/"}, ""

    monkeypatch.setattr(scrape, "_fetch_pinned", fake_fetch)
    assert scrape.fetch_text("https://shop.example.com/") == ""
    assert used == ["93.184.216.34"]


def test_redirects_are_capped(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    hops = []

    def loop(parts, ip, timeout):
        hops.append(1)
        return 302, {"location": "/again"}, ""

    monkeypatch.setattr(scrape, "_fetch_pinned", loop)
    assert scrape.fetch_text("https://shop.example.com/") == ""
    assert len(hops) == scrape._MAX_REDIRECTS + 1


def test_public_page_text_extracted(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    monkeypatch.setattr(scrape, "_fetch_pinned", lambda parts, ip, t: (200, {"content-type": "text/html"}, PAGE))
    assert scrape.fetch_text("shop.example.com") == "Hello"


# --- owner password lockout -------------------------------------------------

ENV = {"ANA_ADMIN": "1", "ANA_ADMIN_PASSWORD": "s3cret-test"}


def test_visitor_locked_after_repeated_wrong_guesses():
    g = admin.LoginGuard(per_visitor=3, global_limit=100, window=900)
    for i in range(3):
        assert admin.try_login("nope", g, "ip:1.1.1.1", ENV, now=1000 + i) == "wrong"
    # Even the right password is refused while locked.
    assert admin.try_login("s3cret-test", g, "ip:1.1.1.1", ENV, now=1010) == "locked"
    assert admin.try_login("s3cret-test", g, "ip:2.2.2.2", ENV, now=1010) == "ok"
    assert admin.try_login("s3cret-test", g, "ip:1.1.1.1", ENV, now=1000 + 901) == "ok"


def test_global_lockout_when_visitor_unknown_or_rotating():
    g = admin.LoginGuard(per_visitor=3, global_limit=5, window=900)
    for i in range(5):
        assert admin.try_login("nope", g, f"ip:9.9.9.{i}" if i % 2 else None, ENV, now=1000 + i) == "wrong"
    assert admin.try_login("s3cret-test", g, None, ENV, now=1010) == "locked"
    assert admin.try_login("s3cret-test", g, "ip:8.8.8.8", ENV, now=1010) == "locked"


def test_failed_attempt_logged_without_the_value(caplog):
    g = admin.LoginGuard()
    with caplog.at_level("WARNING", logger="ana.admin"):
        admin.try_login("my-guess-XYZ", g, None, ENV)
    assert "wrong attempt" in caplog.text
    assert "my-guess-XYZ" not in caplog.text


def test_login_guard_memory_is_bounded():
    g = admin.LoginGuard(max_keys=50)
    for i in range(500):
        g.failure(f"ip:10.0.{i // 256}.{i % 256}", now=1000)
    assert len(g._fails) <= 50
    assert len(g._global) <= g.global_limit
