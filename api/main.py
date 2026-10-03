"""ana API — the product backend (Phase 1: encrypted key vault + health).

The chat engine (src/) is wired in a later phase; this build exposes the secure
BYOK key vault and a health check, ready to be extended with auth and multi-tenancy.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api import vault

app = FastAPI(title="ana API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ana"}


class SecretIn(BaseModel):
    name: str
    secret: str


@app.get("/vault/keys")
def list_keys() -> dict:
    # names only — secret values are never exposed by listing
    return {"keys": vault.list_names()}


@app.post("/vault/keys")
def put_key(body: SecretIn) -> dict:
    vault.put(body.name, body.secret)
    return {"saved": body.name}


@app.delete("/vault/keys/{name}")
def delete_key(name: str) -> dict:
    if not vault.delete(name):
        raise HTTPException(status_code=404, detail="key not found")
    return {"deleted": name}


@app.post("/chat")
def chat(body: dict) -> dict:
    # wired to src/ engine in the next phase
    return {"error": "engine not wired in this build", "status": "unavailable"}
