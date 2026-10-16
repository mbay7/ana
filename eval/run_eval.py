"""Retrieval eval with a pass mark — recall@5, MRR, and "I don't know" counts.

Deterministic and cheap (no LLM calls). This is the number that tells us
whether a change to retrieval actually helps, and the gate that stops a change
that makes Ana worse.

Gate (eval/thresholds.json, "never worse than today"):
  - dense recall@5 on the 50 answerable questions >= min_hits_at5
  - "I don't know" on answerable questions <= max_wrong_idk  (Ana gave up when she had the answer)
  - "I don't know" on unanswerable questions >= min_right_idk (Ana declined instead of guessing)
"I don't know" uses the live rule: Ana abstains when her top retrieval
confidence is below the client's retrieval.threshold.

Exit code 0 = pass, 1 = below the bar. Use --k / --threshold to run a
deliberately lowered check and prove the gate fails.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent
THRESHOLDS = HERE / "thresholds.json"


def hit(got, need, category):
    if category == "multi_chunk":
        return set(need).issubset(set(got))
    return bool(set(need) & set(got))


def rr(got, need):
    for rank, s in enumerate(got, start=1):
        if s in need:
            return 1.0 / rank
    return 0.0


def check(metrics, thresholds):
    """Return a list of plain-language failures (empty list = pass)."""
    fails = []
    if metrics["dense_hits"] < thresholds["min_hits_at5"]:
        fails.append(
            f"found the right document for {metrics['dense_hits']}/{metrics['answerable']} questions "
            f"(needs at least {thresholds['min_hits_at5']})"
        )
    if metrics["wrong_idk"] > thresholds["max_wrong_idk"]:
        fails.append(
            f"said \"I don't know\" to {metrics['wrong_idk']} questions she could answer "
            f"(allowed at most {thresholds['max_wrong_idk']})"
        )
    if metrics["right_idk"] < thresholds["min_right_idk"]:
        fails.append(
            f"declined only {metrics['right_idk']}/{metrics['unanswerable']} questions she can't answer "
            f"(needs at least {thresholds['min_right_idk']})"
        )
    return fails


def load_thresholds(path=THRESHOLDS):
    t = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("min_hits_at5", "max_wrong_idk", "min_right_idk"):
        if not isinstance(t.get(key), int) or t[key] < 0:
            raise ValueError(f"eval/thresholds.json: '{key}' must be a non-negative whole number")
    return t


def build(cfg):
    from src.bm25 import BM25
    from src.chunking import chunk_documents
    from src.embed import Embedder
    from src.loaders import load_markdown_dir

    docs = load_markdown_dir(cfg["corpus_dir"])
    chunks = chunk_documents(docs)
    embedder = Embedder(cfg["model"]["embed"])
    vecs = embedder.embed([c.text for c in chunks])
    bm25 = BM25([c.text for c in chunks])
    return chunks, vecs, bm25, embedder


def evaluate(cfg, k=5, threshold=None):
    from src.retrieve import retrieve

    chunks, vecs, bm25, embedder = build(cfg)
    golden = [json.loads(l) for l in open(HERE / "golden.jsonl", encoding="utf-8")]
    answerable = [q for q in golden if q["category"] in ("answerable", "multi_chunk")]
    unanswerable = [q for q in golden if q["category"] == "unanswerable"]
    if threshold is None:
        threshold = cfg["retrieval"].get("threshold") or 0.0
    live_hybrid = cfg["retrieval"].get("hybrid", False)
    live_top_k = cfg["retrieval"]["top_k"]

    qvec = {q["id"]: embedder.embed([q["question"]])[0] for q in golden}
    m = {"answerable": len(answerable), "unanswerable": len(unanswerable), "k": k, "threshold": threshold}

    for label, use_hybrid in [("dense", False), ("hybrid", True)]:
        hits_n, mrr = 0, 0.0
        for q in answerable:
            got = retrieve(q["question"], qvec[q["id"]], vecs, chunks, bm25=bm25 if use_hybrid else None, top_k=k)
            sources = [d.source for d, _ in got]
            hits_n += hit(sources, q["sources"], q["category"])
            mrr += rr(sources, q["sources"])
        m[f"{label}_hits"] = hits_n
        m[f"{label}_mrr"] = mrr / len(answerable)

    def abstains(q):
        got = retrieve(q["question"], qvec[q["id"]], vecs, chunks, bm25=bm25 if live_hybrid else None, top_k=live_top_k)
        return (not got) or got[0][1] < threshold

    m["wrong_idk"] = sum(abstains(q) for q in answerable)
    m["right_idk"] = sum(abstains(q) for q in unanswerable)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=5, help="top-k for recall (default 5; lower it to prove the gate fails)")
    ap.add_argument("--threshold", type=float, default=None, help="override the abstain threshold (default: client config)")
    ap.add_argument("--client", default=None, help="client folder under clients/ (default: CLIENT env or demo)")
    args = ap.parse_args(argv)

    from src.config import load_config

    cfg = load_config(args.client)
    t = load_thresholds()
    m = evaluate(cfg, k=args.k, threshold=args.threshold)
    n = m["answerable"]
    print(f"dense    recall@{m['k']} {m['dense_hits']}/{n} = {m['dense_hits'] / n:.1%}   MRR {m['dense_mrr']:.3f}")
    print(f"hybrid   recall@{m['k']} {m['hybrid_hits']}/{n} = {m['hybrid_hits'] / n:.1%}   MRR {m['hybrid_mrr']:.3f}")
    print(f"I don't know: {m['wrong_idk']}/{n} answerable (bad), {m['right_idk']}/{m['unanswerable']} unanswerable (good)   threshold {m['threshold']}")
    fails = check(m, t)
    if fails:
        print("FAIL — below the quality bar:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("PASS — at or above the quality bar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
