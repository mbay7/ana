"""Engine wrapper — build a client's index once and answer against it, cached per client."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

# chat.py is a root-level module (not under src/); make it importable cwd-independently.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import chat as engine  # noqa: E402
from src.config import load_config  # noqa: E402

_lock = threading.Lock()
_cache: dict[str, tuple] = {}


def get_client(client: str) -> tuple:
    with _lock:
        if client not in _cache:
            cfg = load_config(client)
            _cache[client] = (cfg, engine.build(cfg))
        return _cache[client]


def answer(client: str, question: str, api_key: str | None = None) -> str:
    cfg, state = get_client(client)
    chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers = state
    return engine.ask(
        chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers,
        cfg, question, api_key=api_key,
    )
