"""CLI entrypoint — build the index and answer questions."""
import sys

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
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    return chunks, vecs, embedder, persona


def ask(chunks, vecs, embedder, persona, cfg, question):
    qv = embedder.embed([question])[0]
    hits = retrieve(qv, vecs, chunks, cfg["retrieval"]["top_k"])
    return answer(question, [d for d, _ in hits], persona, cfg["model"]["generate"], cfg.get("max_tokens", 250))


def main():
    cfg = load_config()
    chunks, vecs, embedder, persona = build(cfg)
    print(f"built index: {len(chunks)} chunks")
    qs = sys.argv[1:] or [
        "What's the difference between Glow Milk and Skin Tint?",
        "How do I get glazed skin?",
    ]
    for q in qs:
        print(f"\nQ: {q}\nA: {ask(chunks, vecs, embedder, persona, cfg, q)}")


if __name__ == "__main__":
    main()