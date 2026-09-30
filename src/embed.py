"""Local embedding model wrapper (sentence-transformers)."""
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]):
        return self.model.encode(texts, normalize_embeddings=True)