# SPDX-License-Identifier: Apache-2.0
"""Retrieval metrics + Reciprocal Rank Fusion — thin wrapper over `ranx`."""

from __future__ import annotations

from ranx import Qrels, Run, evaluate, fuse

QrelsDict = dict[str, dict[str, int]]
RunDict = dict[str, dict[str, float]]

DEFAULT_METRICS: tuple[str, ...] = ("ndcg@10", "recall@100", "recall@1000")


def evaluate_run(
    qrels: QrelsDict,
    run: RunDict,
    metrics: list[str] | None = None,
) -> dict[str, float]:
    """Compute retrieval metrics (default: nDCG@10, Recall@100, Recall@1000).

    Returns a dict mapping each metric label to its mean across queries.
    """
    if metrics is None:
        metrics = list(DEFAULT_METRICS)
    qrels_obj = Qrels(qrels)
    run_obj = Run(run)
    result = evaluate(qrels_obj, run_obj, metrics)
    if isinstance(result, dict):
        return {k: float(v) for k, v in result.items()}
    return {metrics[0]: float(result)}


def rrf_fuse(runs: list[RunDict], k: int = 60) -> RunDict:
    """Reciprocal Rank Fusion (Cormack et al., SIGIR 2009): score = sum 1/(k + rank).

    With 0 or 1 runs, returns the input unchanged (no fusion needed). With >=2 runs,
    delegates to ranx.fuse(method='rrf').
    """
    if not runs:
        return {}
    if len(runs) == 1:
        return {qid: dict(docs) for qid, docs in runs[0].items()}
    run_objs = [Run(r, name=f"run_{i}") for i, r in enumerate(runs)]
    fused = fuse(run_objs, method="rrf", params={"k": k})
    return {qid: dict(docs) for qid, docs in fused.to_dict().items()}
