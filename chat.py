"""CLI entrypoint — build the index and answer questions."""
import sys

from src.analytics import log
from src.bm25 import BM25
from src.chunking import chunk_documents
from src.config import load_config
from src.customers import identify, load_customers, profile_prompt
from src.embed import Embedder
from src.generate import answer, checkout, greet, is_buy_intent, is_chitchat, is_farewell, is_greeting, is_medical_request, is_routine_intent, is_thanks, is_vague_product_request, recommend, routine, small_talk_reply
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


def ask(chunks, vecs, bm25, embedder, persona, catalog, catalog_vecs, customers, cfg, question, api_key=None, memory=None):
    qv = embedder.embed([question])[0]
    model = cfg["model"]["generate"]
    max_tokens = cfg.get("max_tokens", 250)
    log_path = cfg["analytics_log"]
    memory = memory if memory is not None else {}
    if is_greeting(question):
        out = greet(question, persona, model, max_tokens=140, api_key=api_key)
        if out is None:
            log(log_path, question=question, answered=False, source="greeting", confidence=None, error="generation failed")
            return "Hi there! I can help you find products, check delivery, and sort returns. What are you looking for?"
        log(log_path, question=question, answered=True, source="greeting", confidence=None)
        return out
    if is_thanks(question):
        out = small_talk_reply("thanks", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="thanks", confidence=None, error="generation failed")
            return "You're welcome! Anything else I can help you find?"
        log(log_path, question=question, answered=True, source="thanks", confidence=None)
        return out
    if is_farewell(question):
        out = small_talk_reply("farewell", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="farewell", confidence=None, error="generation failed")
            return "Thanks for stopping by, see you next time!"
        log(log_path, question=question, answered=True, source="farewell", confidence=None)
        return out
    if is_vague_product_request(question):
        out = small_talk_reply("vague", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="vague", confidence=None, error="generation failed")
            return "I can help you find something! What kind of product are you looking for?"
        log(log_path, question=question, answered=True, source="vague", confidence=None)
        return out
    if is_chitchat(question):
        out = small_talk_reply("chitchat", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="chitchat", confidence=None, error="generation failed")
            return "Sounds good! Anything I can help you find?"
        log(log_path, question=question, answered=True, source="chitchat", confidence=None)
        return out
    if is_medical_request(question):
        out = small_talk_reply("medical", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="medical", confidence=None, error="generation failed")
            return "I can't give medical advice. It's best to check with a doctor or dermatologist. I'm still happy to help you find a product if you'd like."
        log(log_path, question=question, answered=True, source="medical", confidence=None)
        return out
    customer = identify(question, customers, enabled=(cfg.get("customers") or {}).get("enabled", False))
    cust_ctx = profile_prompt(customer) if customer else None
    matches = recommend_products(qv, catalog, catalog_vecs)
    # Retrieval is cheap to compute up front, and lets us prefer a store-info
    # answer (policy, delivery, returns) over an incidental product match.
    use_hybrid = cfg["retrieval"].get("hybrid", False)
    hits = retrieve(question, qv, vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=cfg["retrieval"]["top_k"])
    top_conf = hits[0][1] if hits else 0.0
    threshold = cfg["retrieval"].get("threshold")
    if is_buy_intent(question):
        # Resolve "I'll take it" to the last product we recommended, so a
        # checkout intent without a named product checks out the right thing.
        prod = matches[0][0] if matches else memory.get("last_product")
        if prod:
            out = checkout(question, prod, persona, model, api_key=api_key, customer_ctx=cust_ctx, prelaunch=cfg.get("checkout", {}).get("prelaunch", False))
            memory.pop("last_product", None)
            log(
                log_path, question=question, answered=(out is not None),
                source="checkout:" + prod.get("name", ""), confidence=(matches[0][1] if matches else None),
                error=(None if out is not None else "generation failed"),
            )
            return out if out is not None else "Sorry, I couldn't pull that up just now. Try again in a moment."
        out = small_talk_reply("buy_which", persona, model, api_key=api_key, question=question)
        if out is None:
            log(log_path, question=question, answered=False, source="buy_which", confidence=None, error="generation failed")
            return "Which one were you after? Tell me the name and I'll sort you out."
        log(log_path, question=question, answered=True, source="buy_which", confidence=None)
        return out
    if is_routine_intent(question) and cfg.get("routine_enabled", False):
        prods = [p for p, _ in matches] if matches else catalog
        out = routine(question, prods, persona, model, max_tokens=max_tokens, customer_ctx=cust_ctx, api_key=api_key)
        log(
            log_path, question=question, answered=(out is not None),
            source="routine", confidence=(matches[0][1] if matches else None),
            error=(None if out is not None else "generation failed"),
        )
        return out if out is not None else "Sorry, I couldn't pull that together just now. Try again in a moment."
    if matches and matches[0][1] > top_conf:
        prods = [p for p, _ in matches]
        memory["last_product"] = prods[0]
        out = recommend(question, prods, persona, model, max_tokens=max_tokens, customer_ctx=cust_ctx, api_key=api_key)
        log(
            log_path, question=question, answered=(out is not None),
            source="catalog:" + prods[0].get("name", ""), confidence=matches[0][1],
            error=(None if out is not None else "generation failed"),
        )
        return out if out is not None else "Sorry, I couldn't pull that up just now. Try again in a moment."
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