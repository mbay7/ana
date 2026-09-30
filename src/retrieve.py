"""Top-k dense retrieval via cosine similarity."""
import numpy as np

from .schema import Document


def retrieve(query_vec, doc_vecs, docs: list[Document], top_k: int) -> list[tuple[Document, float]]:
    sims = doc_vecs @ query_vec
    order = np.argsort(-sims)[:top_k]
    return [(docs[i], float(sims[i])) for i in order]