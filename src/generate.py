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


def answer(question, hits, persona, model, max_tokens=250, threshold=None, abstain=None, api_key=None, customer_ctx=None):
    """hits: list of (Document, confidence). Abstain when top confidence < threshold."""
    if threshold is not None and hits and hits[0][1] < threshold:
        return abstain or DEFAULT_ABSTAIN
    ctx = "\n\n".join(f"[{d.source}] {d.text}" for d, _ in hits)
    system = persona if not customer_ctx else persona + "\n\n" + customer_ctx
    out = _complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Use ONLY this info, in the persona's voice:\n\n{ctx}\n\nQuestion: {question}"},
        ],
        model, max_tokens, api_key,
    )
    return out if out is not None else "[no API key configured]"


def recommend(question, products, persona, model, max_tokens=250, api_key=None, customer_ctx=None):
    """Recommend the best-matching product(s) in the persona's voice, with price + link."""
    lines = [
        f"- {p.get('name','')} ({p.get('price','?')}): {p.get('description','')} [link: {p.get('link','')}]"
        for p in products
    ]
    catalog = "\n".join(lines)
    base = persona if not customer_ctx else persona + "\n\n" + customer_ctx
    sys = (
        base
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


_GREETING_WORDS = {"hi", "hello", "hey", "hiya", "howdy", "salam", "salaam", "مرحبا", "اهلا", "هاي"}
_GREETING_PATTERNS = (
    "how can you help", "how can i help", "what can you do", "what do you do",
    "who are you", "what are you", "what can i ask",
)


def is_greeting(text: str) -> bool:
    """Detect greetings and 'what can you do' small-talk, before retrieval."""
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 60:
        return False
    first = t.split()[0] if t.split() else ""
    if first in _GREETING_WORDS:
        return True
    return any(t.startswith(p) for p in _GREETING_PATTERNS)


def greet(question, persona, model, max_tokens=140, api_key=None) -> str:
    """Warm, persona-voiced greeting that introduces what the assistant can do."""
    system = (
        persona
        + "\n\nThe shopper just greeted you or asked what you can do. Greet them back warmly, "
        "introduce yourself as this store's assistant in your natural voice, and say in one or "
        "two short lines what you can help with: finding and recommending products, delivery, and returns."
    )
    out = _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": question}],
        model, max_tokens, api_key,
    )
    return out if out is not None else (
        "Hi there! I can help you find products, check delivery, and sort returns. What are you looking for?"
    )


_THANKS = {"thanks", "thank", "thx", "cheers", "شكرا", "شكراً", "مشكور"}
_FAREWELL = {"bye", "goodbye", "farewell", "باى", "باي", "مع السلامة", "وداعا", "الى اللقاء", "الوداع"}


def is_thanks(text: str) -> bool:
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 40:
        return False
    return t.startswith(("thank you", "thanks", "thank")) or any(w in _THANKS for w in t.split())


def is_farewell(text: str) -> bool:
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 40:
        return False
    return t in _FAREWELL or any(t.startswith(w) for w in _FAREWELL) or t.startswith("see you")


_SMALLTALK_PROMPTS = {
    "thanks": "The shopper just thanked you. Reply warmly and briefly in your voice, and invite them to ask anything else (products, recommendations, delivery, returns).",
    "farewell": "The shopper just said goodbye. Reply with a warm, brief farewell in your voice, and invite them back anytime.",
}
_SMALLTALK_FALLBACKS = {
    "thanks": "You're welcome! Anything else I can help you find?",
    "farewell": "Thanks for stopping by, see you next time!",
}


def small_talk_reply(kind, persona, model, max_tokens=80, api_key=None):
    system = persona + "\n\n" + _SMALLTALK_PROMPTS[kind]
    out = _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": kind}],
        model, max_tokens, api_key,
    )
    return out if out is not None else _SMALLTALK_FALLBACKS[kind]