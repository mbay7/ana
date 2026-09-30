# Retrieval ablation

Deterministic metrics (no LLM in the loop). Top-5 source-file recall and MRR
on the golden set (50 answerable + multi-chunk questions, each with a known
source file).

| config | recall@5 | MRR   |
|--------|----------|-------|
| dense  | 94.0%    | 0.724 |
| hybrid | 88.0%    | 0.595 |

Dense (MiniLM cosine) wins on this corpus. Hybrid (BM25 + dense via reciprocal
rank fusion) slightly hurts, because the corpus has few exact-term queries
where keyword matching adds signal: BM25's equal vote dilutes the good dense
matches.

Decision: ship dense. Hybrid stays available (`retrieval.hybrid` in config) and
is the right call for corpora heavy in exact terms like SKUs, product codes,
model names, or IDs.