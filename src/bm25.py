"""Okapi BM25 — classic keyword ranking, implemented in numpy (no external dep).

Pairs with the dense embedder in hybrid search: dense handles meaning,
BM25 handles exact terms (product codes, names, policy numbers).
"""
import math
import re
from collections import Counter

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = [tokenize(d) for d in docs]
        self.n = len(self.corpus)
        self.doc_len = np.array([len(c) for c in self.corpus], dtype=float)
        self.avgdl = self.doc_len.mean() if self.n else 1.0
        self.df = Counter()
        for c in self.corpus:
            self.df.update(set(c))
        self.idf = {
            t: math.log(1 + (self.n - df + 0.5) / (df + 0.5))
            for t, df in self.df.items()
        }

    def get_scores(self, query: str) -> np.ndarray:
        scores = np.zeros(self.n)
        for t in _TOKEN.findall(query.lower()):
            idf = self.idf.get(t, 0.0)
            if idf == 0.0:
                continue
            for i, c in enumerate(self.corpus):
                tf = c.count(t)
                if tf:
                    denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                    scores[i] += idf * tf * (self.k1 + 1) / denom
        return scores