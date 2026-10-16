"""Stage 1 step 8 — one access code per brand; only listed websites may call Ana.

Done when brand A's code is refused for brand B (test_brand_a_code_is_refused_for_brand_b).
The engine is replaced with a stub, so no model is loaded and nothing is spent.
"""
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import api.main as main
from api import vault

OWNER = "owner-test-token"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ANA_API_TOKEN", OWNER)
    monkeypatch.setenv("ANA_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("ANA_DASHBOARD_ORIGINS", raising=False)
    monkeypatch.setattr(vault, "STORE_FILE", tmp_path / "vault.json")
    monkeypatch.setattr(vault, "KEY_FILE", tmp_path / ".vault_key")
    monkeypatch.setattr(main.engine_mod, "answer", lambda brand, q, api_key=None: f"[{brand}] answer")
    return TestClient(main.app)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def issue(c, brand):
    r = c.post(f"/assistants/{brand}/access-code", headers=bearer(OWNER))
    assert r.status_code == 200
    return r.json()["access_code"]


def ask(c, brand, token, origin=None):
    h = bearer(token)
    if origin:
        h["Origin"] = origin
    return c.post(f"/assistants/{brand}/chat", json={"question": "What are your opening hours?"}, headers=h)


def test_brand_a_code_is_refused_for_brand_b(client):
    code_demo = issue(client, "demo")
    issue(client, "arabic")
    assert ask(client, "demo", code_demo).status_code == 200
    r = ask(client, "arabic", code_demo)
    assert r.status_code == 403
    assert "not valid for this assistant" in r.json()["detail"]


def test_brand_code_answers_its_own_brand(client):
    code = issue(client, "demo")
    r = ask(client, "demo", code)
    assert r.status_code == 200 and r.json()["answer"] == "[demo] answer"


def test_owner_token_reaches_every_brand(client):
    assert ask(client, "demo", OWNER).status_code == 200
    assert ask(client, "arabic", OWNER).status_code == 200


def test_unknown_code_and_missing_token_are_refused(client):
    issue(client, "demo")
    assert ask(client, "demo", "ana_made-up").status_code == 403
    assert client.post("/assistants/demo/chat", json={"question": "hi"}).status_code == 401


def test_brand_with_no_code_issued_refuses_everyone_but_owner(client):
    assert ask(client, "arabic", "ana_anything").status_code == 403
    assert ask(client, "arabic", OWNER).status_code == 200


def test_reissued_code_replaces_the_old_one(client):
    old = issue(client, "demo")
    new = issue(client, "demo")
    assert old != new
    assert ask(client, "demo", old).status_code == 403
    assert ask(client, "demo", new).status_code == 200


def test_listed_website_is_allowed(client):
    code = issue(client, "demo")
    assert ask(client, "demo", code, origin="https://ana.mblab.ai").status_code == 200


def test_unlisted_website_is_refused_even_with_the_right_code(client):
    code = issue(client, "demo")
    r = ask(client, "demo", code, origin="https://copycat.example")
    assert r.status_code == 403 and "website is not allowed" in r.json()["detail"]


def test_brand_a_website_cannot_call_brand_b(client):
    issue(client, "arabic")
    # arabic lists no websites; demo's website must not reach it even with the owner token
    assert ask(client, "arabic", OWNER, origin="https://ana.mblab.ai").status_code == 403


def test_owner_dashboard_origin_is_allowed(client, monkeypatch):
    monkeypatch.setenv("ANA_DASHBOARD_ORIGINS", "https://dash.mblab.ai")
    assert ask(client, "arabic", OWNER, origin="https://dash.mblab.ai").status_code == 200


def test_brand_code_cannot_touch_the_vault_or_issue_codes(client):
    code = issue(client, "demo")
    assert client.get("/vault/keys", headers=bearer(code)).status_code == 401
    assert client.post("/vault/keys", json={"name": "arabic:openrouter", "secret": "x"}, headers=bearer(code)).status_code == 401
    assert client.post("/assistants/arabic/access-code", headers=bearer(code)).status_code == 401
    assert client.get("/assistants", headers=bearer(code)).status_code == 401


def test_vault_listing_never_shows_codes(client):
    issue(client, "demo")
    r = client.get("/vault/keys", headers=bearer(OWNER))
    assert r.status_code == 200 and r.json()["keys"] == ["demo:access"]


@pytest.mark.parametrize("brand", ["_template", "../clients", "Demo", "nope"])
def test_hidden_bad_or_unknown_brands_are_not_found(client, brand):
    assert ask(client, brand, OWNER).status_code in (404, 405)


def test_engine_errors_do_not_leak_details(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret internal path /srv/ana/keys")

    monkeypatch.setattr(main.engine_mod, "answer", boom)
    r = ask(client, "demo", OWNER)
    assert r.status_code == 500 and "/srv" not in r.text


def test_fails_closed_without_owner_token(client, monkeypatch):
    monkeypatch.delenv("ANA_API_TOKEN")
    assert ask(client, "demo", "anything").status_code == 503
