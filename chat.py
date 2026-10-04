"""CLI entrypoint — build the index and answer questions."""
import sys

from src.analytics import log
from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.customers import identify, load_customers, profile_prompt
from src.embed import Embedder
from src.generate import answer, greet, is_farewell, is_greeting, is_thanks, recommend, small_talk_reply
from src.loaders import load_markdown_dir
from src.recommend import embed_catalog, load_catalog, recommend_products
from src.retrieve import retrieve
from src import shopify


def build(cfg):
    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    persona = open(cfg["persona_file"], encoding="utf-8").read()
    if shopify.configured(cfg):
        catalog = shopify.fetch_catalog(cfg)
        customers = shopify.fetch_customers(cfg)
    else:
        catalog = load_catalog(cfg.get("catalog_file"))
        customers = load_customers(cfg.get("customers_file"))
    catalog_vecs = embed_catalog(catalog, embedder)
    return chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers


def ask(chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers, cfg, question, api_key=None):
    qv = embedder.embed([question])[0]
    model = cfg["model"]["generate"]
    max_tokens = cfg.get("max_tokens", 250)
    log_path = cfg["analytics_log"]
    if is_greeting(question):
        out = greet(question, persona, model, max_tokens=140, api_key=api_key)
        if out is None:
            log(log_path, question=question, answered=False, source="greeting", confidence=None, error="generation failed")
            return "Hi there! I can help you find products, check delivery, and sort returns. What are you looking for?"
        return out
    if is_thanks(question):
        out = small_talk_reply("thanks", persona, model, api_key=api_key)
        if out is None:
            log(log_path, question=question, answered=False, source="thanks", confidence=None, error="generation failed")
            return "You're welcome! Anything else I can help you find?"
        return out
    if is_farewell(question):
        out = small_talk_reply("farewell", persona, model, api_key=api_key)
        if out is None:
            log(log_path, question=question, answered=False, source="farewell", confidence=None, error="generation failed")
            return "Thanks for stopping by, see you next time!"
        return out
    customer = identify(question, customers)
    cust_ctx = profile_prompt(customer) if customer else None
    matches = recommend_products(qv, catalog, catalog_vecs)
    if matches:
        prods = [p for p, _ in matches]
        out = recommend(question, prods, persona, model, max_tokens=max_tokens, customer_ctx=cust_ctx, api_key=api_key)
        log(
            log_path, question=question, answered=(out is not None),
            source="catalog:" + prods[0].get("name", ""), confidence=matches[0][1],
            error=(None if out is not None else "generation failed"),
        )
        return out if out is not None else "Sorry, I couldn't pull that up just now. Try again in a moment."
    use_hybrid = cfg["retrieval"].get("hybrid", False)
    hits = retrieve(question, qv, vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=cfg["retrieval"]["top_k"])
    top_conf = hits[0][1] if hits else 0.0
    threshold = cfg["retrieval"].get("threshold")
    out = answer(question, hits, persona, model, max_tokens=max_tokens, threshold=threshold, customer_ctx=cust_ctx, api_key=api_key)
    log(
        log_path, question=question,
        answered=(out is not None and (top_conf >= (threshold or 0.0))),
        source=(hits[0][0].source if hits else None), confidence=top_conf,
        error=(None if out is not None else "generation failed"),
    )
    return out if out is not None else "Sorry, I can't answer that right now. Try again in a moment."


def main():
    cfg = load_config()
    chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers = build(cfg)
    print(f"built index: {len(chunks)} chunks, {len(catalog)} products, {len(customers)} customers")
    qs = sys.argv[1:] or [
        "How quickly does normal UK delivery take?",
        "What lamp should I get for a cozy bedroom?",
        "Hi, I'm Sarah. Can I return the duvet I bought?",
        "What's the capital of France?",  # should abstain
    ]
    for q in qs:
        print(f"\nQ: {q}\nA: {ask(chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers, cfg, q)}")


if __name__ == "__main__":
    main()