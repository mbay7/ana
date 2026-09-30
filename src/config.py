"""Load configuration from YAML."""
from pathlib import Path

import yaml


def load_config(path: str = "config/default.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))