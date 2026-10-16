# Ana — a reusable retrieval-augmented chat assistant

A small, clean engine that answers customer questions from a brand's own
documents, in a configurable voice. One engine, many clients: each client is a
self-contained folder, and the core does not change between them.

## What it does

1. Loads a folder of markdown (the brand's products, policies, and voice).
2. Splits it into chunks and embeds each chunk locally (free, on-device).
3. Finds the most relevant chunks for a question.
4. Answers in a configured persona voice, using only the retrieved context,
   or abstains ("I don't know") when nothing is relevant enough.

## Structure

```
ana/
  app.py                 # Streamlit chat UI (repo-root entry)
  chat.py                # CLI: ask questions from the terminal
  clients/
    demo/                # fictional demo client (safe to publish)
      config.yaml        # brand, model, retrieval, ui, channels
      persona.txt        # the voice
      corpus/            # their markdown
    _template/           # blank template — copy to onboard a new client
    README.md            # onboarding + deploy guide
  src/
    schema.py            # Document dataclass (the contract between stages)
    loaders.py           # markdown dir -> [Document]
    chunking.py          # heading-aware chunking
    embed.py             # embedding model wrapper
    bm25.py              # Okapi BM25 keyword ranking (numpy, no dep)
    retrieve.py          # dense + hybrid retrieval, reciprocal rank fusion
    generate.py          # persona-prompted LLM answer + abstention threshold
    config.py            # loads clients/<name>/config.yaml
  eval/                  # golden set + deterministic retrieval metrics
```

## Run it

```bash
uv venv .venv && uv pip install -r requirements.txt
export OPENROUTER_API_KEY=...   # or keep it in a .env (gitignored)

python chat.py "How quickly does normal UK delivery take?"   # one question
python chat.py                                               # the example questions
streamlit run app.py                                         # chat UI at localhost:8501
```

Run a different client with `CLIENT=<name>` (defaults to `demo`).

## Evaluation

`eval/run_eval.py` scores retrieval on a golden set. Deterministic and cheap
(no LLM in the loop), so it is the first thing to check after any change.

| config | recall@5 | MRR   |
|--------|----------|-------|
| dense  | 94.0%    | 0.724 |
| hybrid | 88.0%    | 0.595 |

Dense wins on this corpus, so it is the default. Hybrid (BM25 + dense) is
available via `retrieval.hybrid` and is the better choice for corpora heavy in
exact terms like SKUs, product codes, or model names. Full write-up in
`eval/results/ablation.md`.

## Onboarding a new client

Copy `clients/_template/` to `clients/<your-client>/`, fill in the config,
persona, and corpus. No core code changes. See `clients/README.md`.

## Notes

- Embeddings use `all-MiniLM-L6-v2` locally. The generator model, top-k,
  abstention threshold, and hybrid flag are set per client in their
  `config.yaml` and can be swapped freely.
- Answers are grounded in the provided context only, and the persona is told
  to say it does not know rather than invent. The abstention threshold makes
  that a hard guarantee instead of a hope.

## Privacy and limits

- **What is logged:** each question (to `data/<client>.jsonl`), whether it was answered, the top
  source and the confidence. Before writing, emails, phone numbers and order-like numbers are
  replaced with `[email]`, `[phone]`, `[order]` or `[number]`.
- **How long it is kept:** 30 days. Older rows are deleted every time a new row is written.
  Change it with `ANA_LOG_RETENTION_DAYS` (`0` keeps everything).
- **Limits:** message length (500 characters); messages per minute for the whole server
  (always on); messages per minute and per hour per visitor, kept on the server so a reload
  does not reset them (only when `ANA_BEHIND_CLOUDFLARE=1`, since the visitor's address is
  otherwise forgeable); messages per chat; and a monthly spend ceiling per brand, with each
  message's likely cost held before the model is called. If the spend file cannot be read or
  written, Ana refuses rather than overspends. See `.env.example` for the setting names.
  **The real per-address limit must also be set at Cloudflare**; the in-app one is a backstop.
- **Owner pages (Usage, Build):** off unless both `ANA_ADMIN=1` and `ANA_ADMIN_PASSWORD` are set,
  and the password is entered. After 5 wrong guesses from one visitor, or 20 from anyone, in
  15 minutes, the password box locks. Wrong attempts are logged without what was typed.
- **Website reader (Build):** only public http(s) sites; the address is checked once and the
  connection goes to that checked address, at most 5 redirects, each checked again.

## Licence

Ana is source-available under the PolyForm Noncommercial License 1.0.0 (see `LICENSE`).
You may read, fork, and run this code to learn from it for personal, research, educational,
and other noncommercial purposes. You may not use it commercially or offer it as a product
or service without written permission from the author.

Real client data never appears in this repository. `clients/demo/` is a fictional store. A
client's confidential corpus, persona, and catalogue live outside this repo and are never
committed.