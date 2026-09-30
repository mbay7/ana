"""Retrieval eval — recall@5 and MRR, dense-only vs hybrid (BM25 + dense).

Deterministic and cheap (no LLM calls). This is the number that tells us
whether a change to retrieval actually helps.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.embed import Embedder
from src.loaders import load_markdown_dir
from src.retrieve import retrieve


def build(cfg):
    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    return chunks, vecs, bm25, embedder


def hit(got, need, category):
    if category == "multi_chunk":
        return set(need).issubset(set(got))
    return bool(set(need) & set(got))


def rr(got, need):
    for rank, s in enumerate(got, start=1):
        if s in need:
            return 1.0 / rank
    return 0.0


def main():
    cfg = load_config()
    chunks, vecs, bm25, embedder = build(cfg)
    golden = [json.loads(l) for l in open("eval/golden.jsonl", encoding="utf-8")]
    qs = [q for q in golden if q["category"] in ("answerable", "multi_chunk")]

    for label, use_hybrid in [("dense", False), ("hybrid", True)]:
        hits_n = 0
        mrr = 0.0
        for q in qs:
            qv = embedder.embed([q["question"]])[0]
            got = retrieve(q["question"], qv, vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=5)
            sources = [d.source for d, _ in got]
            hits_n += hit(sources, q["sources"], q["category"])
            mrr += rr(sources, q["sources"])
        n = len(qs)
        print(f"{label:7s}  recall@5 {hits_n}/{n} = {hits_n / n:.1%}   MRR {mrr / n:.3f}")


if __name__ == "__main__":
    main()