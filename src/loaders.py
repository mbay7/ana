"""Load a directory of markdown files into Document objects."""
from pathlib import Path

from .schema import Document


def load_markdown_dir(corpus_dir: str, exclude_readme: bool = True) -> list[Document]:
    docs: list[Document] = []
    for p in sorted(Path(corpus_dir).glob("*.md")):
        if exclude_readme and p.name.lower() == "readme.md":
            continue
        docs.append(Document(id=p.stem, text=p.read_text(encoding="utf-8"), source=p.name))
    return docs