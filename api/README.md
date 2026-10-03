# ana API

The product backend for ana. Wraps the RAG engine (`src/`) as a multi-client HTTP service.

## Endpoints

- `GET /health` — liveness.
- `GET /assistants` — list client folders with a `config.yaml`.
- `POST /assistants/{client}/chat` — `{"question": "..."}` → grounded answer.
- `GET /vault/keys` — key names only (never values).
- `POST /vault/keys` — store a BYOK secret, encrypted. `{"name", "secret"}`.
- `DELETE /vault/keys/{name}` — remove a secret.

## Security

- BYOK keys are encrypted at rest with Fernet (AES + HMAC). The vault key comes
  from `ANA_VAULT_KEY` or a chmod-600 file, never the repo.
- A per-client key stored as `{client}:openrouter` overrides the shared
  `OPENROUTER_API_KEY` env fallback.
- Bind to `127.0.0.1`; no public port. The kill switch stops and wipes in one command.

## Run

```
pip install -r api/requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8011
```

## Kill switch

```
bash scripts/killswitch.sh
```

Stops the API and wipes the index, analytics and vault in one command.
