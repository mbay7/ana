"""Split documents into retrieval-friendly chunks.

Simple and defensible for now: split on blank lines (each paragraph or product
blob is its own chunk), drop pure-heading lines and fragments that are too
short to be useful on their own. A fancier doc-type-aware strategy (keep each
Q&A pair whole, sliding windows for long policy pages) is a later upgrade.
"""
import re

from .schema import Document


def chunk_document(doc: Document, min_chars: int = 20) -> list[Document]:
    blocks = re.split(r"\n\s*\n", doc.text)
    out: list[Document] = []
    current_heading = ""
    for i, block in enumerate(blocks):
        body: list[str] = []
        for line in block.rstrip("\n").split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                current_heading = stripped.lstrip("#").strip()
                continue
            body.append(line)
        text = "\n".join(body).strip()
        if len(text) < min_chars:
            continue
        if current_heading:
            text = f"{current_heading}: {text}"
        out.append(
            Document(
                id=f"{doc.id}:{i}",
                text=text,
                source=doc.source,
                metadata={"chunk": i, "heading": current_heading},
            )
        )
    return out


def chunk_documents(docs: list[Document], min_chars: int = 30) -> list[Document]:
    chunks: list[Document] = []
    for d in docs:
        chunks.extend(chunk_document(d, min_chars=min_chars))
    return chunks