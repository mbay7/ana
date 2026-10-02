"""Customer memory: identify who is chatting and build their profile context.

This is the demo baseline for customer profiling. A real deployment would source
identity and history from the client's CRM/Shopify (HMAC login, OTP email, or a
pre-chat form) rather than a local file, but the shape — load a profile, inject
who the customer is into the answer — is the same.
"""
import json
import re
from pathlib import Path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def load_customers(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        return data.get("customers", [])
    return data if isinstance(data, list) else []


def identify(message, customers) -> dict | None:
    """Return the customer this message is most likely from, or None."""
    if not customers or not message:
        return None
    m = _EMAIL.search(message)
    if m:
        email = m.group(0).lower()
        for c in customers:
            if (c.get("email") or "").lower() == email:
                return c
    low = " " + message.lower() + " "
    for c in customers:
        name = (c.get("name") or "").strip().lower()
        first = name.split()[0] if name else ""
        if not first:
            continue
        for pat in ("i'm ", "i am ", "im ", "this is "):
            if (pat + first) in low:
                return c
    return None


def profile_prompt(customer) -> str:
    """A prompt block telling the assistant who it is talking to."""
    name = customer.get("name", "the customer")
    email = customer.get("email")
    who = f"The human you are talking to is {name}" + (f" ({email})." if email else ".")
    parts = [who]
    orders = customer.get("past_orders") or []
    if orders:
        parts.append("Their past orders: " + "; ".join(orders) + ".")
    prefs = customer.get("preferences") or []
    if prefs:
        parts.append("Their known preferences: " + "; ".join(prefs) + ".")
    parts.append(
        "Acknowledge them by name when natural and use this history where it helps. "
        "Never invent orders or preferences beyond what is listed."
    )
    return " ".join(parts)