"""Retrieval: dense cosine, plus hybrid (BM25 + dense) with reciprocal rank fusion.

`retrieve` returns hits as (Document, dense_confidence) tuples. The confidence
is the dense cosine similarity, so a caller can threshold on it to abstain.
"""
import numpy as np

from .schema import Document


def _ranks(scores: np.ndarray) -> np.ndarray:
    # best (highest score) -> rank 0 so 1/(k + rank) is largest for the best item
    order = np.argsort(-scores)
    ranks = np.empty_like(scores)
    ranks[order] = np.arange(scores.shape[0])
    return ranks


def rrf(dense: np.ndarray, sparse: np.ndarray, k: int = 60) -> np.ndarray:
    """Reciprocal rank fusion of two score vectors."""
    return 1.0 / (k + _ranks(dense)) + 1.0 / (k + _ranks(sparse))


def retrieve(query, query_vec, doc_vecs, docs, bm25=None, top_k=4, k=60):
    dense = doc_vecs @ query_vec
    if bm25 is not None:
        sparse = bm25.get_scores(query)
        fused = rrf(dense, sparse, k=k)
        order = np.argsort(-fused)[:top_k]
    else:
        order = np.argsort(-dense)[:top_k]
    return [(docs[i], float(dense[i])) for i in order]