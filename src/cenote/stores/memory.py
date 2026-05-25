# SPDX-License-Identifier: Apache-2.0
"""InMemoryVectorStore — dict + numpy cosine similarity. For demos and tests."""

from __future__ import annotations

from typing import Any

import numpy as np

from cenote.errors import ConfigurationError, DimensionMismatchError
from cenote.models import EmbeddedChunk, RetrievalResult


class InMemoryVectorStore:
    """Per-namespace dicts of EmbeddedChunks. Cosine similarity via numpy."""

    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise ConfigurationError("dimensions must be positive")
        self._dimensions = dimensions
        self._data: dict[str, dict[str, EmbeddedChunk]] = {}

    async def upsert(self, embedded_chunks: list[EmbeddedChunk], namespace: str) -> None:
        bucket = self._data.setdefault(namespace, {})
        for ec in embedded_chunks:
            if len(ec.embedding) != self._dimensions:
                raise DimensionMismatchError(
                    f"embedding dim {len(ec.embedding)} != store dim {self._dimensions}"
                )
            bucket[ec.chunk.id] = ec

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if len(query_vector) != self._dimensions:
            raise DimensionMismatchError(
                f"query dim {len(query_vector)} != store dim {self._dimensions}"
            )
        bucket = self._data.get(namespace)
        if not bucket:
            return []
        q = np.asarray(query_vector, dtype=np.float64)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return []
        scored: list[tuple[float, EmbeddedChunk]] = []
        for ec in bucket.values():
            if filter and not _matches_filter(ec.chunk.metadata, filter):
                continue
            v = np.asarray(ec.embedding, dtype=np.float64)
            v_norm = float(np.linalg.norm(v))
            if v_norm == 0.0:
                continue
            score = float(np.dot(q, v) / (q_norm * v_norm))
            scored.append((score, ec))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [
            RetrievalResult(chunk=ec.chunk, score=score, retriever="vector")
            for score, ec in scored[:limit]
        ]

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        bucket = self._data.get(namespace)
        if not bucket:
            return
        for cid in chunk_ids:
            bucket.pop(cid, None)

    async def delete_namespace(self, namespace: str) -> None:
        self._data.pop(namespace, None)


def _matches_filter(metadata: dict[str, Any], filter: dict[str, Any]) -> bool:
    """Exact-match all filter keys against metadata."""
    return all(metadata.get(key) == expected for key, expected in filter.items())
