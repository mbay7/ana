"""CLI entrypoint — build the index and answer questions."""
import sys

from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.embed import Embedder
from src.generate import answer
from src.loaders import load_markdown_dir
from src.retrieve import retrieve


def build(cfg):
    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    return chunks, vecs, bm25, embedder, persona


def ask(chunks, vecs, bm25, embedder, persona, cfg, question):
    qv = embedder.embed([question])[0]
    use_hybrid = cfg["retrieval"].get("hybrid", False)
    hits = retrieve(question, qv, vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=cfg["retrieval"]["top_k"])
    return answer(
        question, hits, persona, cfg["model"]["generate"],
        max_tokens=cfg.get("max_tokens", 250),
        threshold=cfg["retrieval"].get("threshold"),
    )


def main():
    cfg = load_config()
    chunks, vecs, bm25, embedder, persona = build(cfg)
    print(f"built index: {len(chunks)} chunks")
    qs = sys.argv[1:] or [
        "How quickly does normal UK delivery take?",
        "Can I return something I changed my mind about?",
        "What's the capital of France?",  # should abstain
    ]
    for q in qs:
        print(f"\nQ: {q}\nA: {ask(chunks, vecs, bm25, embedder, persona, cfg, q)}")


if __name__ == "__main__":
    main()