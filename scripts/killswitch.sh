#!/usr/bin/env bash
# ana kill switch — one command that stops the API and wipes the index + vault.
# Usage: bash scripts/killswitch.sh   (respects ANA_DATA_DIR like the app does)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${ANA_DATA_DIR:-$ROOT/data}"

echo "== ana kill switch =="

if pkill -f "uvicorn api.main:app" 2>/dev/null; then
  echo "  API stopped"
else
  echo "  API not running"
fi

rm -f "$DATA_DIR"/*.jsonl "$DATA_DIR"/built.json 2>/dev/null && echo "  index + analytics wiped"
rm -f "$DATA_DIR"/vault.json "$DATA_DIR"/.vault_key 2>/dev/null && echo "  vault wiped (new key generated on next start)"

echo "Done. Everything is stopped and wiped."
