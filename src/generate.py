"""Answer a question from retrieved context, and recommend products, persona-prompted."""
import json
import os
import urllib.request

from .schema import Document

DEFAULT_ABSTAIN = "I'm not sure about that, and I'd rather not guess. Let me connect you with a human who can help."
_URL = "https://openrouter.ai/api/v1/chat/completions"


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


def _complete(messages, model, max_tokens=250, api_key=None):
    key = api_key or _api_key()
    if not key:
        return None
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}
    req = urllib.request.Request(
        _URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def answer(question, hits, persona, model, max_tokens=250, threshold=None, abstain=None, api_key=None):
    """hits: list of (Document, confidence). Abstain when top confidence < threshold."""
    if threshold is not None and hits and hits[0][1] < threshold:
        return abstain or DEFAULT_ABSTAIN
    ctx = "\n\n".join(f"[{d.source}] {d.text}" for d, _ in hits)
    out = _complete(
        [
            {"role": "system", "content": persona},
            {"role": "user", "content": f"Use ONLY this info, in the persona's voice:\n\n{ctx}\n\nQuestion: {question}"},
        ],
        model, max_tokens, api_key,
    )
    return out if out is not None else "[no API key configured]"


def recommend(question, products, persona, model, max_tokens=250, api_key=None):
    """Recommend the best-matching product(s) in the persona's voice, with price + link."""
    lines = [
        f"- {p.get('name','')} ({p.get('price','?')}): {p.get('description','')} [link: {p.get('link','')}]"
        for p in products
    ]
    catalog = "\n".join(lines)
    sys = (
        persona
        + "\n\nThe shopper wants a product recommendation. Pick the best match(es) from this list, "
        "say briefly WHY each fits their need, and give the name, price and link. Keep it warm and "
        "short, and do not invent anything that is not in the list."
    )
    out = _complete(
        [
            {"role": "system", "content": sys},
            {"role": "user", "content": f"Question: {question}\n\nProducts:\n{catalog}"},
        ],
        model, max_tokens, api_key,
    )
    return out if out is not None else "[no API key configured]"