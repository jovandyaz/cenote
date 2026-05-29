# SPDX-License-Identifier: Apache-2.0
"""HybridRetriever — Reciprocal Rank Fusion over N base retrievers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from cenote.errors import ConfigurationError
from cenote.models import Chunk, RetrievalResult
from cenote.retrievers.base import Retriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Fuses results from multiple Retrievers via Reciprocal Rank Fusion.

    Score for chunk `c` is `sum(weights[i] / (k_constant + rank_in_retriever_i))`
    over every retriever where `c` appears. k_constant defaults to 60 per
    Cormack et al. (SIGIR 2009).

    Each base retriever is called with a wider candidate pool than the final
    `limit` so RRF has room to combine across them — see `candidate_pool_size`.

    N=1 is allowed for composability/benchmarking; the output `retriever`
    field is still `"hybrid"` regardless of how many bases were fused.
    """

    def __init__(
        self,
        retrievers: list[Retriever],
        weights: list[float] | None = None,
        k_constant: int = 60,
        candidate_pool_size: int | None = None,
    ) -> None:
        if not retrievers:
            raise ConfigurationError("retrievers must be non-empty")
        if weights is not None and len(weights) != len(retrievers):
            raise ConfigurationError("weights length must match retrievers length")
        if k_constant <= 0:
            raise ConfigurationError("k_constant must be positive")
        if candidate_pool_size is not None and candidate_pool_size <= 0:
            raise ConfigurationError("candidate_pool_size must be positive")
        self._retrievers = retrievers
        self._weights = weights if weights is not None else [1.0] * len(retrievers)
        self._k = k_constant
        self._pool_size = candidate_pool_size

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        pool = self._pool_size if self._pool_size is not None else max(limit * 4, 100)
        results_or_exc = await asyncio.gather(
            *[
                r.retrieve(query, namespace=namespace, limit=pool, filter=filter)
                for r in self._retrievers
            ],
            return_exceptions=True,
        )
        results: list[list[RetrievalResult]] = []
        for i, item in enumerate(results_or_exc):
            if isinstance(item, BaseException):
                logger.warning(
                    "HybridRetriever: base retriever %d (%s) failed: %s",
                    i,
                    type(self._retrievers[i]).__name__,
                    item,
                )
                results.append([])
            else:
                results.append(item)
        fused_scores: dict[str, float] = {}
        first_seen: dict[str, Chunk] = {}
        for weight, batch in zip(self._weights, results, strict=True):
            for rank, r in enumerate(batch):
                contrib = weight / (self._k + rank + 1)
                fused_scores[r.chunk.id] = fused_scores.get(r.chunk.id, 0.0) + contrib
                first_seen.setdefault(r.chunk.id, r.chunk)
        ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)
        out = [
            RetrievalResult(
                chunk=first_seen[cid],
                score=fused_scores[cid],
                retriever="hybrid",
            )
            for cid in ranked_ids[:limit]
        ]
        logger.debug(
            "HybridRetriever: fused %d unique chunks from %d retrievers",
            len(ranked_ids),
            len(self._retrievers),
        )
        return out
