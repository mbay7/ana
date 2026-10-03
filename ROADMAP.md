# Roadmap

Noor, a reusable multi-client RAG assistant for brand support and shopping. Live demo at
https://shopassist-agent.streamlit.app — this repo is the engine behind it.

## Shipped

- **Answer engine** — grounded RAG over a brand's policies/FAQs, with a confidence
  threshold that abstains ("connect you with a human") instead of guessing.
- **Product recommendation** — a structured catalog matched by embedding; the agent
  recommends with a reason, price, and link.
- **Customer memory** — recognizes a returning customer (email or name) and
  personalizes from their order history and preferences.
- **Multi-client** — each brand is a self-contained `clients/<name>/` folder with its
  own config, persona, corpus, catalog, and customers. Adding a new one needs no code.
- **Analytics** — JSONL usage log plus a "Usage" view (answered vs deflected, top sources).
- **Arabic** — multilingual embedding plus right-to-left UI; language is config, not code.
- **Self-serve onboarding** — paste content, upload files, or import a website URL and
  get a working assistant in minutes (a "Build" view).
- **Shopify read (BYOK)** — live products, customers, and orders swap in for the static
  files when a store and token are provided.

## Retrieval quality

Dense recall@5 **94%** (47/50), MRR 0.724, on a 50-question golden set; hybrid is 88%.
See `eval/` for the set, the runner, and the ablation table.

## Next

1. Order-status lookup ("where's my order") and Shopify write actions (returns/refunds),
   gated behind human approval.
2. WhatsApp connector (Meta Cloud API).
3. Shareable link + site embed widget.
4. Human handoff with full context passed to the human.
5. Vision (photos of damaged goods / returns) and voice.
6. Proactive outreach + cart recovery.
7. Cloud persistence (a real database) — file persistence is local-only.