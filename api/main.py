"""ana API — the product backend.

Phase 1: encrypted BYOK key vault + health.
Phase 2: multi-client chat engine wired in, assistants listed from clients/.
Phase 3: bearer-token auth so protected endpoints never go public open.
Phase 4 (Stage 1 step 8): one access code per brand, and only the brand's
listed websites may call it.

Two kinds of token:
- Owner token (ANA_API_TOKEN env): the vault, the assistant list, issuing brand
  access codes, and chat with any brand.
- Brand access code (stored encrypted in the vault as "<brand>:access"): chat
  with that one brand only. Brand A's code is refused for brand B.
Browser calls must also come from one of the brand's `allowed_origins`
(clients/<brand>/config.yaml) or the owner dashboard (ANA_DASHBOARD_ORIGINS).
"""
from __future__ import annotations

import logging
import os
import re
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api import engine as engine_mod
from api import vault
from src.config import load_config

CLIENTS_DIR = Path(__file__).resolve().parent.parent / "clients"
BRAND_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
log = logging.getLogger("ana.api")

app = FastAPI(title="ana API", version="0.4.0")


def _dashboard_origins() -> list[str]:
    return [o.strip() for o in os.environ.get("ANA_DASHBOARD_ORIGINS", "").split(",") if o.strip()]


def _brand_exists(brand: str) -> bool:
    return bool(BRAND_RE.match(brand)) and (CLIENTS_DIR / brand / "config.yaml").exists()


def _brand_origins(brand: str) -> list[str]:
    if not _brand_exists(brand):
        return []
    return [str(o).rstrip("/") for o in (load_config(brand).get("allowed_origins") or [])]


def _all_allowed_origins() -> list[str]:
    origins = set(_dashboard_origins())
    for d in CLIENTS_DIR.iterdir():
        if d.is_dir() and not d.name.startswith("_") and _brand_exists(d.name):
            origins.update(_brand_origins(d.name))
    return sorted(origins)


# Browsers only get answers for listed websites. CORS is not authentication —
# every protected endpoint also checks a token below.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_allowed_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    return authorization.removeprefix("Bearer ")


def _is_owner(token: str) -> bool:
    expected = os.environ.get("ANA_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="ANA_API_TOKEN not configured")
    return secrets.compare_digest(token, expected)


def require_owner(authorization: str | None = Header(default=None)) -> None:
    """Owner-only guard. Fails closed when ANA_API_TOKEN is unset."""
    if not _is_owner(_bearer(authorization)):
        raise HTTPException(status_code=401, detail="invalid token")


def require_brand(brand: str, request: Request, authorization: str | None = Header(default=None)) -> None:
    """Chat guard: the owner token, or this brand's own access code — and, for
    browser calls, an Origin listed for this brand."""
    if not _brand_exists(brand) or brand.startswith("_"):
        raise HTTPException(status_code=404, detail="assistant not found")
    token = _bearer(authorization)
    if not _is_owner(token):
        expected = vault.get(f"{brand}:access")
        if not expected or not secrets.compare_digest(token, expected):
            raise HTTPException(status_code=403, detail="this access code is not valid for this assistant")
    origin = request.headers.get("origin")
    if origin is not None:
        allowed = set(_brand_origins(brand)) | set(_dashboard_origins())
        if origin.rstrip("/") not in allowed:
            raise HTTPException(status_code=403, detail="this website is not allowed to use this assistant")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ana", "version": "0.4.0"}


class SecretIn(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}:[a-z0-9_-]{1,40}$")
    secret: str = Field(min_length=1, max_length=4096)


@app.get("/vault/keys", dependencies=[Depends(require_owner)])
def list_keys() -> dict:
    # names only — secret values are never exposed by listing
    return {"keys": vault.list_names()}


@app.post("/vault/keys", dependencies=[Depends(require_owner)])
def put_key(body: SecretIn) -> dict:
    vault.put(body.name, body.secret)
    return {"saved": body.name}


@app.delete("/vault/keys/{name}", dependencies=[Depends(require_owner)])
def delete_key(name: str) -> dict:
    if not vault.delete(name):
        raise HTTPException(status_code=404, detail="key not found")
    return {"deleted": name}


@app.post("/assistants/{brand}/access-code", dependencies=[Depends(require_owner)])
def issue_access_code(brand: str) -> dict:
    """Create (or replace) a brand's access code. Shown once — store it in the
    brand's website settings; Ana keeps only the encrypted copy."""
    if not _brand_exists(brand) or brand.startswith("_"):
        raise HTTPException(status_code=404, detail="assistant not found")
    code = "ana_" + secrets.token_urlsafe(32)
    vault.put(f"{brand}:access", code)
    return {"brand": brand, "access_code": code, "note": "shown once; replaces any previous code"}


def _list_clients() -> list[dict]:
    out = []
    for d in sorted(CLIENTS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and (d / "config.yaml").exists():
            cfg = load_config(d.name)
            out.append(
                {
                    "name": d.name,
                    "title": cfg.get("name", d.name),
                    "subtitle": (cfg.get("ui") or {}).get("subtitle", ""),
                }
            )
    return out


@app.get("/assistants", dependencies=[Depends(require_owner)])
def list_assistants() -> dict:
    return {"assistants": _list_clients()}


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/assistants/{brand}/chat", dependencies=[Depends(require_brand)])
def chat(brand: str, body: ChatIn) -> dict:
    # BYOK: a per-brand key stored in the vault overrides the shared env key.
    api_key = vault.get(f"{brand}:openrouter")
    try:
        text = engine_mod.answer(brand, body.question, api_key=api_key)
    except Exception:  # noqa: BLE001 — never leak internals to the caller
        log.exception("engine error for brand %s", brand)
        raise HTTPException(status_code=500, detail="Ana could not answer just now. Please try again.")
    return {"client": brand, "answer": text}
