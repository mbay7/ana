"""Load a client's configuration from clients/<name>/config.yaml.

A client is a self-contained folder: corpus/ (their content), persona.txt
(their voice), and config.yaml (brand, language, model, channels). The engine
under src/ is generic; everything client-specific lives in that one folder.

Select the client with the CLIENT env var or by passing a name; defaults to
"demo". Paths are resolved to absolute so the app is cwd-independent.
"""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(client: str | None = None) -> dict:
    name = client or os.environ.get("CLIENT", "demo")
    cdir = ROOT / "clients" / name
    cfg = yaml.safe_load((cdir / "config.yaml").read_text(encoding="utf-8"))

    # resolve content paths against the client folder (absolute, cwd-independent)
    cfg["corpus_dir"] = str(cdir / cfg.get("corpus_dir", "corpus"))
    cfg["persona_file"] = str(cdir / cfg.get("persona_file", "persona.txt"))
    cfg["catalog_file"] = str(cdir / cfg.get("catalog_file", "catalog.yaml"))
    cfg["analytics_log"] = str(ROOT / "data" / f"{name}.jsonl")
    cfg["_client"] = name
    cfg["_client_dir"] = str(cdir)
    return cfg