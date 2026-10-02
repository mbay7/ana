import src.shopify as shopify

PRODUCTS = {
    "products": [
        {
            "id": 1,
            "title": "Brass Table Lamp",
            "body_html": "<p>warm brass</p>",
            "tags": "lamp, bedroom",
            "variants": [{"price": "68.00"}],
            "handle": "brass-table-lamp",
        }
    ]
}

CUSTOMERS = {
    "customers": [
        {
            "id": 10,
            "first_name": "Sarah",
            "last_name": "S",
            "email": "sarah@x.com",
            "tags": "neutral, natural",
        }
    ]
}

ORDERS = {"orders": [{"name": "#1001", "line_items": [{"title": "Linen Duvet"}]}]}


def _fake_get(url, token):
    if "products" in url:
        return PRODUCTS
    if "customers" in url:
        return CUSTOMERS
    if "orders" in url:
        return ORDERS
    return {}


CFG = {"shopify": {"store": "demo.myshopify.com", "token": "shpat_fake"}}


def test_configured_requires_store_and_token():
    assert shopify.configured(CFG)
    assert not shopify.configured({})


def test_fetch_catalog_maps_product(monkeypatch):
    monkeypatch.setattr(shopify, "_get_json", _fake_get)
    cat = shopify.fetch_catalog(CFG)
    assert cat[0]["name"] == "Brass Table Lamp"
    assert cat[0]["price"] == "68.00"
    assert cat[0]["link"].endswith("/products/brass-table-lamp")
    assert "lamp" in cat[0]["attributes"]


def test_fetch_customers_maps_profile(monkeypatch):
    monkeypatch.setattr(shopify, "_get_json", _fake_get)
    cust = shopify.fetch_customers(CFG)
    assert cust[0]["name"] == "Sarah S"
    assert cust[0]["past_orders"] == ["order #1001: Linen Duvet"]
    assert cust[0]["preferences"] == ["neutral", "natural"]