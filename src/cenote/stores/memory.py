# SPDX-License-Identifier: Apache-2.0
"""InMemoryVectorStore — dict + numpy cosine similarity. For demos and tests."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

import numpy as np

from cenote._filters import matches_filter
from cenote.errors import ConfigurationError, DimensionMismatchError
from cenote.models import Chunk, EmbeddedChunk, RetrievalResult
from cenote.types import Vector

logger = logging.getLogger(__name__)


class InMemoryVectorStore:
    """Per-namespace dicts of EmbeddedChunks. Cosine similarity via numpy."""

    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise ConfigurationError("dimensions must be positive")
        self._dimensions = dimensions
        self._data: dict[str, dict[str, EmbeddedChunk]] = {}

    async def upsert(self, embedded_chunks: list[EmbeddedChunk], namespace: str) -> None:
        bucket = self._data.setdefault(namespace, {})
        logger.debug("InMemoryVectorStore.upsert: ns=%s count=%d", namespace, len(embedded_chunks))
        for ec in embedded_chunks:
            if len(ec.embedding) != self._dimensions:
                raise DimensionMismatchError(
                    f"embedding dim {len(ec.embedding)} != store dim {self._dimensions}"
                )
            bucket[ec.chunk.id] = ec

    async def search(
        self,
        query_vector: Vector,
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
            logger.debug("InMemoryVectorStore.search: ns=%s is empty", namespace)
            return []
        q = np.asarray(query_vector, dtype=np.float64)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return []
        scored: list[tuple[float, EmbeddedChunk]] = []
        for ec in bucket.values():
            if filter and not matches_filter(ec.chunk.metadata, filter):
                continue
            v = np.asarray(ec.embedding, dtype=np.float64)
            v_norm = float(np.linalg.norm(v))
            if v_norm == 0.0:
                continue
            score = float(np.dot(q, v) / (q_norm * v_norm))
            scored.append((score, ec))
        scored.sort(key=lambda t: t[0], reverse=True)
        logger.debug(
            "InMemoryVectorStore.search: ns=%s returned %d of %d candidates",
            namespace,
            min(len(scored), limit),
            len(scored),
        )
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

    async def get_all_chunks(
        self,
        namespace: str,
        filter: dict[str, Any] | None = None,
    ) -> AsyncIterator[Chunk]:
        bucket = self._data.get(namespace, {})
        for ec in bucket.values():
            if filter and not matches_filter(ec.chunk.metadata, filter):
                continue
            yield ec.chunk
