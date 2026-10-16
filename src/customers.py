"""Customer memory: identify who is chatting and build their profile context.

This is the demo baseline for customer profiling. A real deployment would source
identity and history from the client's CRM/Shopify (HMAC login, OTP email, or a
pre-chat form) rather than a local file, but the shape — load a profile, inject
who the customer is into the answer — is the same.
"""
import json
from pathlib import Path


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


def identify(message, customers, enabled=False, session_customer_id=None) -> dict | None:
    """Return the customer for a signed-in session, or None.

    Identity must come from an authenticated session (a customer id the store's
    login has verified), never from free-form text a shopper types. Without a
    session id nothing is looked up, even when customers are enabled, so no name,
    email or order history reaches the prompt from chat text. `message` is kept
    for call compatibility and is not used for matching.
    """
    if not enabled or not customers or not session_customer_id:
        return None
    wanted = str(session_customer_id)
    for c in customers:
        if str(c.get("id", "")) == wanted:
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