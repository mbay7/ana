"""Document contract — the single data type every stage passes around."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    id: str
    text: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)