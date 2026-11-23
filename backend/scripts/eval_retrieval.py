"""Measure retrieval quality against eval/questions.json (no LLM calls).

Usage: python -m scripts.eval_retrieval
Reports hit@k (is any expected chunk in the top-k?) and MRR, and lists misses.
Run it after every change to the knowledge base or the chunking.
"""
import json
from pathlib import Path

from app import rag
from app.config import BASE_DIR, get_settings
from app.store import ensure_index


def main():
    collection = ensure_index()
    k = get_settings().top_k
    cases = json.loads((BASE_DIR / "eval" / "questions.json").read_text())

    hits, rr_total, misses = 0, 0.0, []
    for case in cases:
        retrieved = [p["id"] for p in rag.retrieve(collection, case["question"], [], k)]
        rank = next(
            (i for i, cid in enumerate(retrieved, 1) if cid in case["expected_ids"]), None
        )
        if rank:
            hits += 1
            rr_total += 1 / rank
        else:
            misses.append((case["question"], case["expected_ids"], retrieved))

    n = len(cases)
    print(f"hit@{k}: {hits}/{n} = {hits / n:.0%}   MRR: {rr_total / n:.2f}")
    for question, expected, got in misses:
        print(f"\nMISS: {question}\n  expected one of: {expected}\n  got: {got}")


if __name__ == "__main__":
    main()
