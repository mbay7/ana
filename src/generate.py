"""Answer a question from retrieved context with a persona-prompted LLM."""
import json
import os
import urllib.request

from .schema import Document

DEFAULT_ABSTAIN = "I'm not sure about that, and I'd rather not guess. Let me connect you with a human who can help."


def _api_key() -> str | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    env_path = os.environ.get("HERMES_HOME", "/opt/data") + "/.env"
    try:
        for line in open(env_path):
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return None


def answer(question, hits, persona, model, max_tokens=250, threshold=None, abstain=None, api_key=None):
    """hits: list of (Document, confidence). Abstain when top confidence < threshold."""
    if threshold is not None and hits and hits[0][1] < threshold:
        return abstain or DEFAULT_ABSTAIN

    key = api_key or _api_key()
    if not key:
        return "[no API key configured]"

    ctx = "\n\n".join(f"[{d.source}] {d.text}" for d, _ in hits)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": persona},
            {"role": "user", "content": f"Use ONLY this info, in the persona's voice:\n\n{ctx}\n\nQuestion: {question}"},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()