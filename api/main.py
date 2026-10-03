"""ana API — the product backend.

Phase 1: encrypted BYOK key vault + health.
Phase 2: multi-client chat engine wired in, assistants listed from clients/.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api import engine as engine_mod
from api import vault
from src.config import load_config

CLIENTS_DIR = Path(__file__).resolve().parent.parent / "clients"

app = FastAPI(title="ana API", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ana", "version": "0.2.0"}


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


@app.get("/assistants")
def list_assistants() -> dict:
    return {"assistants": _list_clients()}


class ChatIn(BaseModel):
    question: str


@app.post("/assistants/{client}/chat")
def chat(client: str, body: ChatIn) -> dict:
    if not (CLIENTS_DIR / client / "config.yaml").exists():
        raise HTTPException(status_code=404, detail="assistant not found")
    # BYOK: a per-client key stored in the vault overrides the shared env key.
    api_key = vault.get(f"{client}:openrouter")
    try:
        text = engine_mod.answer(client, body.question, api_key=api_key)
    except Exception as e:  # noqa: BLE001 — surface engine errors to the caller
        raise HTTPException(status_code=500, detail=f"engine error: {e}") from e
    return {"client": client, "answer": text}
