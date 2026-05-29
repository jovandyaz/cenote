# SPDX-License-Identifier: Apache-2.0
"""Pyserini-2cr-style markdown report for cenote benchmarks."""

from __future__ import annotations

from typing import Final

_RETRIEVER_LABEL: Final[dict[str, str]] = {
    "bm25": "BM25",
    "vector": "Vector",
    "hybrid": "Hybrid (RRF)",
}


def generate_markdown_report(
    *,
    metrics: dict[str, dict[str, float]],
    dataset: str,
    embedder: str,
    commit: str,
    generated_at: str,
) -> str:
    """Render a deterministic Pyserini-2cr-style markdown table for one benchmark run.

    `metrics` keys are retriever names ("bm25" | "vector" | "hybrid") whose values
    must include `ndcg@10`, `recall@100`, `recall@1000`. All scores are rendered to
    four decimal places. Result is byte-for-byte deterministic for the same inputs.
    """
    rows = "\n".join(
        f"| {_RETRIEVER_LABEL.get(name, name):<15} "
        f"| {scores['ndcg@10']:.4f} "
        f"| {scores['recall@100']:.4f} "
        f"| {scores['recall@1000']:.4f} |"
        for name, scores in metrics.items()
    )
    return f"""# Retrieval benchmarks

## {dataset}

Methodology: Pyserini-2cr. Metrics computed via [ranx](https://github.com/AmenRa/ranx)
over TREC-format run files. Reproducible with `cenote bench miracl-es`.

| Retriever        | nDCG@10 | Recall@100 | Recall@1000 |
|------------------|--------:|-----------:|------------:|
{rows}

**Provenance** — embedder: `{embedder}` · commit: `{commit}` · generated: {generated_at}
"""
