"""Shopify Admin API client (read-only) + mappers to the engine's catalog and
customer-memory shapes.

BYOK: the client provides their store domain and an Admin API access token. The
token is read from SHOPIFY_ACCESS_TOKEN (env) or cfg["shopify"]["token"], never
hardcoded and never committed to the public repo. Read-only on purpose (products,
customers, orders) — real write actions come later, behind human approval.

When cfg has a `shopify` block with `store` + a reachable token, the build step
uses live Shopify data instead of the static catalog/customers files. The mapped
shapes are identical, so the engine downstream is unchanged.
"""
import html
import json
import os
import re
import urllib.request

_API_VERSION = "2025-01"


def configured(cfg) -> bool:
    store = (cfg.get("shopify") or {}).get("store", "").strip()
    return bool(store and _token(cfg))


def _token(cfg) -> str:
    return (
        (cfg.get("shopify") or {}).get("token")
        or os.environ.get("SHOPIFY_ACCESS_TOKEN")
        or os.environ.get("SHOPIFY_API_TOKEN")
        or ""
    ).strip()


def _version(cfg) -> str:
    return (cfg.get("shopify") or {}).get("api_version", _API_VERSION)


def _get_json(url, token):
    req = urllib.request.Request(
        url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _store(cfg) -> str:
    return (cfg.get("shopify") or {})["store"].strip()


def _strip_html(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>", " ", html.unescape(s)).strip()


def fetch_catalog(cfg) -> list[dict]:
    """Shopify products mapped to the recommendation-catalog shape."""
    store = _store(cfg)
    url = f"https://{store}/admin/api/{_version(cfg)}/products.json?limit=250"
    data = _get_json(url, _token(cfg))
    out = []
    for p in data.get("products", []):
        price = ""
        variants = p.get("variants") or []
        if variants:
            price = variants[0].get("price") or ""
        out.append({
            "id": str(p.get("id")),
            "name": p.get("title") or "",
            "description": _strip_html(p.get("body_html")),
            "attributes": [t.strip() for t in (p.get("tags") or "").split(",") if t.strip()],
            "price": price,
            "link": f"https://{store}/products/{p.get('handle')}",
        })
    return out


def fetch_customers(cfg) -> list[dict]:
    """Shopify customers mapped to the customer-memory profile shape."""
    store = _store(cfg)
    token = _token(cfg)
    url = f"https://{store}/admin/api/{_version(cfg)}/customers.json?limit=250"
    data = _get_json(url, token)
    out = []
    for c in data.get("customers", []):
        name = " ".join(x for x in [c.get("first_name"), c.get("last_name")] if x).strip()
        out.append({
            "id": str(c.get("id")),
            "name": name or (c.get("email") or "customer"),
            "email": c.get("email"),
            "past_orders": fetch_customer_orders(store, token, c.get("id"), _version(cfg)),
            "preferences": [t.strip() for t in (c.get("tags") or "").split(",") if t.strip()],
        })
    return out


def fetch_customer_orders(store, token, customer_id, api_version=_API_VERSION, limit=5) -> list[str]:
    url = (
        f"https://{store}/admin/api/{api_version}/orders.json"
        f"?customer_id={customer_id}&limit={limit}&status=any"
    )
    data = _get_json(url, token)
    out = []
    for o in data.get("orders", []):
        items = ", ".join((li.get("title") or "") for li in (o.get("line_items") or []))
        out.append(f"order {o.get('name')}: {items}")
    return out