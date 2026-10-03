# Noor — a reusable retrieval-augmented chat assistant

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
noor/
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

## Licence

Noor is source-available under the PolyForm Noncommercial License 1.0.0 (see `LICENSE`).
You may read, fork, and run this code to learn from it for personal, research, educational,
and other noncommercial purposes. You may not use it commercially or offer it as a product
or service without written permission from the author.

Real client data never appears in this repository. `clients/demo/` is a fictional store. A
client's confidential corpus, persona, and catalogue live outside this repo and are never
committed.