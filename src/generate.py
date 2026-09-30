"""Answer a question from retrieved context with a persona-prompted LLM."""
import json
import os
import urllib.request

from .schema import Document


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


def answer(
    question: str,
    contexts: list[Document],
    persona: str,
    model: str,
    max_tokens: int = 200,
    api_key: str | None = None,
) -> str:
    key = api_key or _api_key()
    if not key:
        return "[no API key configured]"

    ctx = "\n\n".join(f"[{d.source}] {d.text}" for d in contexts)
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