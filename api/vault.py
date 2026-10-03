"""Encrypted key vault — stores BYOK secrets (OpenRouter/OpenAI keys, tokens) encrypted at rest.

Security model:
- Secrets are encrypted with Fernet (AES-128-CBC + HMAC, from `cryptography`).
- The vault key never lives in the repo: it comes from `ANA_VAULT_KEY` env, or a
  chmod-600 file generated on first use.
- The store file is chmod-600. Values are never returned by list operations.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_BASE = Path(os.environ.get("ANA_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
KEY_FILE = Path(os.environ.get("ANA_VAULT_KEY_FILE", _BASE / ".vault_key"))
STORE_FILE = Path(os.environ.get("ANA_VAULT_STORE", _BASE / "vault.json"))


def _load_key() -> bytes | None:
    env = os.environ.get("ANA_VAULT_KEY")
    if env:
        return env.encode()
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()
    return None


def _ensure_key() -> bytes:
    key = _load_key()
    if key is None:
        key = Fernet.generate_key()
        _BASE.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_bytes(key)
        os.chmod(KEY_FILE, 0o600)
    return key


def _read_store() -> dict:
    if not STORE_FILE.exists():
        return {}
    try:
        return json.loads(STORE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_store(data: dict) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(json.dumps(data), encoding="utf-8")
    os.chmod(STORE_FILE, 0o600)


def list_names() -> list[str]:
    """Return key names only — never the values."""
    return sorted(_read_store().keys())


def put(name: str, secret: str) -> None:
    f = Fernet(_ensure_key())
    data = _read_store()
    data[name] = f.encrypt(secret.encode()).decode()
    _write_store(data)


def get(name: str) -> str | None:
    token = _read_store().get(name)
    if token is None:
        return None
    f = Fernet(_ensure_key())
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def delete(name: str) -> bool:
    data = _read_store()
    if name not in data:
        return False
    del data[name]
    _write_store(data)
    return True
