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
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
    except Exception:
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    content = (choices[0].get("message") or {}).get("content")
    return content.strip() if isinstance(content, str) else None


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
    return out


def recommend(question, products, persona, model, max_tokens=250, api_key=None, customer_ctx=None):
    """Recommend the best-matching product(s) in the persona's voice, with price + link."""
    lines = []
    for p in products:
        link = p.get("link", "")
        line = f"- {p.get('name','')} ({p.get('price','?')}): {p.get('description','')}"
        if link:
            line += f" [link: {link}]"
        lines.append(line)
    catalog = "\n".join(lines)
    base = persona if not customer_ctx else persona + "\n\n" + customer_ctx
    sys = (
        base
        + "\n\nThe shopper wants a product recommendation. Pick the best match(es) from this list, "
        "say briefly WHY each fits their need, and give the name and price (and the link only if one is listed). Keep it warm and "
        "short, and do not invent anything that is not in the list."
    )
    out = _complete(
        [
            {"role": "system", "content": sys},
            {"role": "user", "content": f"Question: {question}\n\nProducts:\n{catalog}"},
        ],
        model, max_tokens, api_key,
    )
    return out


_GREETING_WORDS = {"hi", "hello", "hey", "hiya", "howdy", "salam", "salaam", "مرحبا", "اهلا", "هاي", "yo", "morning", "afternoon", "evening", "welcome"}
_GREETING_PATTERNS = (
    "how can you help", "how can i help", "what can you do", "what do you do",
    "who are you", "what are you", "what can i ask",
    "how are you", "how r u", "how're you", "how are things", "how are you doing",
    "how is it going", "hows it going", "how's it going", "whats up", "what's up",
    "good morning", "good afternoon", "good evening",
    "what is your name", "whats your name", "what's your name", "your name",
)


def is_greeting(text: str) -> bool:
    """Detect greetings and 'what can you do' small-talk, before retrieval."""
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 60:
        return False
    first = t.split()[0].strip(",،.۔!?؟;؛:： ") if t.split() else ""
    if first in _GREETING_WORDS:
        return True
    return any(t.startswith(p) for p in _GREETING_PATTERNS)


def greet(question, persona, model, max_tokens=140, api_key=None) -> str | None:
    """Warm, persona-voiced greeting that introduces what the assistant can do."""
    system = (
        persona
        + "\n\nThe shopper just greeted you or asked what you can do. Greet them back warmly, like a friend, "
        "and in one or two short lines let them know you can help them find and recommend products and "
        "answer delivery and returns questions. Stay natural and human."
    )
    out = _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": question}],
        model, max_tokens, api_key,
    )
    return out


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
    "vague": "The shopper asked to see products or browse without being specific. In your voice, warmly ask what kind of thing they are looking for, name one or two examples of what the store offers, and offer to help them find it.",
    "chitchat": "The shopper made a light, casual remark or acknowledgment, not a product question. Reply briefly in your voice, warm and human. Keep it short, one or two lines, and gently nudge back toward helping them find something.",
}

_CHITCHAT_ACKS = {
    "nice", "cool", "great", "awesome", "haha", "lol", "ok", "okay", "sure",
    "yes", "no", "maybe", "alright", "yep", "nope", "idk", "not sure", "hmm",
    "hmmm", "bored", "funny", "joke", "wow", "interesting",
}
_CHITCHAT_PHRASES = (
    "tell me a joke", "make me laugh", "i'm bored", "im bored", "i am bored",
    "i like this", "i love this", "love it", "love this", "this is nice",
    "i don't know", "i dont know",
)


def is_chitchat(text: str) -> bool:
    """Detect light casual chit-chat that should get a brief warm reply, not an abstain."""
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 40:
        return False
    if t in _CHITCHAT_ACKS:
        return True
    return any(t.startswith(p) for p in _CHITCHAT_PHRASES)

_VAGUE_PRODUCT_PATTERNS = (
    "find product", "find a product", "find me", "find something",
    "show product", "show me product", "show me products", "show products",
    "browse product", "browse products", "browse",
    "what products do you", "what do you sell", "what do you have",
    "what do you stock", "what products are there", "list product", "list products",
    "see products", "see your products",
    "tell me more", "what else", "what else do you have", "what are your products",
    "what do you offer", "what do you recommend", "recommend something", "im not sure what",
)


def is_vague_product_request(text: str) -> bool:
    """Detect a request to browse products without any specific thing named."""
    t = text.strip().lower().rstrip(".!?؟ ")
    if not t or len(t) > 40:
        return False
    if t in ("products", "product", "catalog", "catalogue"):
        return True
    return any(t.startswith(p) for p in _VAGUE_PRODUCT_PATTERNS)



def small_talk_reply(kind, persona, model, max_tokens=80, api_key=None):
    system = persona + "\n\n" + _SMALLTALK_PROMPTS[kind]
    out = _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": kind}],
        model, max_tokens, api_key,
    )
    return out