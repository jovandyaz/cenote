# SPDX-License-Identifier: Apache-2.0
"""One-time generator for MIRACL-ES + MIRACL-EN subsamples.

Output: src/cenote/eval/datasets/{miracl_es,miracl_en}_subset.jsonl
Run with: `uv run python -m scripts.build_miracl_subset`
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_dataset

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "cenote" / "eval" / "datasets"
SEED = 42
NUM_PASSAGES = 5000
NUM_QUERIES = 200


def build(language: str, filename: str) -> None:
    random.seed(SEED)
    corpus = load_dataset("miracl/miracl-corpus", language, split="train")
    dev = load_dataset("miracl/miracl", language, split="dev")
    queries = list(dev)
    random.shuffle(queries)
    queries = queries[:NUM_QUERIES]
    relevant_docids: set[str] = set()
    qrels: list[dict[str, object]] = []
    for q in queries:
        rel_ids: list[str] = []
        for d in q["positive_passages"]:
            relevant_docids.add(d["docid"])
            rel_ids.append(d["docid"])
        qrels.append({"query_id": q["query_id"], "query": q["query"], "relevant_doc_ids": rel_ids})
    passages = list(corpus)
    random.shuffle(passages)
    sampled = list({p["docid"]: p for p in passages[:NUM_PASSAGES]}.values())
    for pid in relevant_docids:
        if not any(p["docid"] == pid for p in sampled):
            match = next((p for p in passages if p["docid"] == pid), None)
            if match is not None:
                sampled.append(match)
    out_path = OUTPUT_DIR / filename
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "header", "language": language, "qrels": qrels}) + "\n")
        for p in sampled:
            fh.write(
                json.dumps(
                    {"type": "doc", "id": p["docid"], "content": p["text"], "title": p["title"]}
                )
                + "\n"
            )
    print(f"Wrote {len(sampled)} passages + {len(qrels)} queries to {out_path}")


if __name__ == "__main__":
    build("es", "miracl_es_subset.jsonl")
    build("en", "miracl_en_subset.jsonl")
