# Clients

Each client is one self-contained folder. The engine under `src/` is generic;
everything that makes one client different from another lives here.

## Anatomy

```
clients/<name>/
  config.yaml   brand name, language, model, retrieval settings, UI text, channels
  persona.txt   the assistant's voice and rules
  corpus/       their content: shipping, returns, payments, products, FAQ, etc.
```

## Add a client

1. Copy `_template/` to `clients/<your-client>/`.
2. Fill `config.yaml` (name, language, ui, channels).
3. Replace `persona.txt` with their brand voice.
4. Drop their `.md` docs into `corpus/`.
5. Run it: `CLIENT=<your-client> python chat.py`, or set `CLIENT` in the deploy.

## Deploy a client

One deploy = one client. For each client, ship a separate Streamlit Cloud app
(or equivalent) with `CLIENT=<name>` set as an environment variable and the
client's own `OPENROUTER_API_KEY` secret. Same engine, own corpus, own voice,
own keys.

## The demo

`demo/` is a fictional UK retailer (Haven & Hearth) so that no real client or
confidential data ever ships in this public repo. Real client folders are
gitignored and stay local.