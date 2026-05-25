# SPDX-License-Identifier: Apache-2.0
"""Retrieval quality metrics — BEIR-style. M1.1 adds DeepEval integration."""

from __future__ import annotations

from cenote.errors import ConfigurationError
from cenote.models import RetrievalResult


def precision_at_k(
    results: list[RetrievalResult],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Fraction of the top-k retrieved chunks whose IDs are in `relevant_ids`."""
    if k <= 0:
        raise ConfigurationError("k must be positive")
    if not results:
        return 0.0
    top = results[:k]
    hits = sum(1 for r in top if r.chunk.id in relevant_ids)
    return hits / len(top)


def recall_at_k(
    results: list[RetrievalResult],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Fraction of relevant chunks captured by the top-k retrieved results."""
    if k <= 0:
        raise ConfigurationError("k must be positive")
    if not relevant_ids:
        return 0.0
    top_ids = {r.chunk.id for r in results[:k]}
    hits = len(top_ids & relevant_ids)
    return hits / len(relevant_ids)


def mean_reciprocal_rank(
    results: list[RetrievalResult],
    relevant_ids: set[str],
) -> float:
    """Reciprocal of the rank of the first relevant chunk; 0 if none found."""
    for rank, r in enumerate(results, start=1):
        if r.chunk.id in relevant_ids:
            return 1.0 / rank
    return 0.0
