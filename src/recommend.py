"""Product recommendation: match a query to catalog entries by embedding similarity.

The catalog is a structured YAML list of products (name, description, attributes,
price, link). Each product is turned into one text blob and embedded with the same
model as the corpus, so a shopper's question can be matched to products by cosine
similarity. Generic: any client can drop in their own `catalog.yaml`.
"""
import numpy as np
import yaml
from pathlib import Path


def load_catalog(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("products", [])


def catalog_text(product: dict) -> str:
    parts = [product.get("name", ""), product.get("description", "")]
    attrs = product.get("attributes") or product.get("tags") or []
    parts.append(" ".join(attrs))
    return " ".join(parts).strip()


def embed_catalog(catalog, embedder):
    return embedder.embed([catalog_text(p) for p in catalog])


def recommend_products(query_vec, catalog, catalog_vecs, top_k=3, threshold=0.42):
    """Return (product, score) for catalog entries above the similarity threshold."""
    if not catalog or len(catalog_vecs) == 0:
        return []
    scores = np.asarray(catalog_vecs) @ query_vec
    order = np.argsort(-scores)[:top_k]
    return [(catalog[i], float(scores[i])) for i in order if scores[i] >= threshold]