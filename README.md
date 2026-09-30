# Shopassist — a reusable retrieval-augmented chat assistant

A small, clean engine that answers customer questions from a brand's own
documents, in a configurable voice. One engine, many clients: swap the corpus
and the persona, and the core does not change.

## What it does

1. Loads a folder of markdown (the brand's products, policies, and voice).
2. Splits it into chunks and embeds each chunk locally (free, on-device).
3. Finds the most relevant chunks for a question.
4. Answers in a configured persona voice, using only the retrieved context.

## Structure

```
shopassist/
  config/default.yaml   # model names, top-k, thresholds, corpus + persona path
  corpus/               # the knowledge base (markdown) — swap per client
  personas/             # the voice (a system prompt) — swap per client
  src/
    schema.py           # Document dataclass (the contract between stages)
    loaders.py          # markdown dir -> [Document]
    chunking.py         # chunking strategy
    embed.py            # embedding model wrapper
    retrieve.py         # top-k cosine retrieval
    generate.py         # persona-prompted LLM answer
  chat.py               # CLI: ask questions from the terminal
  app/app.py            # Streamlit chat UI
```

## Run it

```bash
uv venv .venv && uv pip install -r requirements.txt
export OPENROUTER_API_KEY=...   # or keep it in a .env (gitignored)

python chat.py "How do I get glazed skin?"   # one question
python chat.py                               # run the example questions
streamlit run app/app.py                     # chat UI at localhost:8501
```

## Onboarding a new client

Add a `corpus/<brand>.md` folder, add a `personas/<brand>.txt`, and point
`config/default.yaml` at both. No core code changes.

## Notes

- Embeddings use `all-MiniLM-L6-v2` locally. The generator model and top-k are
  set in `config/default.yaml` and can be swapped freely.
- Answers are grounded in the provided context only, and the persona is told
  to say it does not know rather than invent.