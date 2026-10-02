"""Persistence for self-serve assistants built in the Build view.

Saves the SOURCE of a built assistant (name, content, voice) as JSON so it
survives an app restart. Chunks and embeddings are re-derived on load, not
stored, so the file stays small and the model can be swapped freely.
"""
import json
import time
from pathlib import Path


def load_all(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save(path, name, content, voice):
    items = load_all(path)
    items.append({"name": name, "content": content, "voice": voice, "created": time.time()})
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def delete(path, index):
    items = load_all(path)
    if 0 <= index < len(items):
        items.pop(index)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return items