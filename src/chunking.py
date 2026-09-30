"""Split documents into retrieval-friendly chunks.

Simple and defensible for now: split on blank lines (each paragraph or product
blob is its own chunk), drop pure-heading lines and fragments that are too
short to be useful on their own. A fancier doc-type-aware strategy (keep each
Q&A pair whole, sliding windows for long policy pages) is a later upgrade.
"""
import re

from .schema import Document


def chunk_document(doc: Document, min_chars: int = 30) -> list[Document]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", doc.text)]
    out: list[Document] = []
    for i, part in enumerate(parts):
        if not part or part.startswith("#"):
            continue
        if len(part) < min_chars:
            continue
        out.append(
            Document(id=f"{doc.id}:{i}", text=part, source=doc.source, metadata={"chunk": i})
        )
    return out


def chunk_documents(docs: list[Document], min_chars: int = 30) -> list[Document]:
    chunks: list[Document] = []
    for d in docs:
        chunks.extend(chunk_document(d, min_chars=min_chars))
    return chunks