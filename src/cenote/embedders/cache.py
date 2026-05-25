# SPDX-License-Identifier: Apache-2.0
"""Caching wrapper around any Embedder."""

from __future__ import annotations

import logging
from typing import Protocol

from cenote.embedders.base import Embedder
from cenote.models import Chunk, EmbeddedChunk
from cenote.types import Vector

logger = logging.getLogger(__name__)


class EmbeddingCache(Protocol):
    """Async key-value store for embedding vectors, keyed by (model_id, content_hash)."""

    async def get(self, model_id: str, content_hash: str) -> Vector | None: ...

    async def set(self, model_id: str, content_hash: str, embedding: Vector) -> None: ...


class InMemoryCache:
    """Dict-backed EmbeddingCache. Suitable for tests and small workloads."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], Vector] = {}

    async def get(self, model_id: str, content_hash: str) -> Vector | None:
        return self._store.get((model_id, content_hash))

    async def set(self, model_id: str, content_hash: str, embedding: Vector) -> None:
        # Store a copy so external mutation of the caller's list cannot poison the cache.
        self._store[(model_id, content_hash)] = list(embedding)


class CachedEmbedder:
    """Wraps an Embedder with an EmbeddingCache.

    On embed(), checks cache per chunk by (model_id, content_hash); only misses
    are forwarded to the inner embedder. Output order matches input order.
    """

    def __init__(self, inner: Embedder, cache: EmbeddingCache) -> None:
        self._inner = inner
        self._cache = cache

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        slots: list[EmbeddedChunk | None] = [None] * len(chunks)
        missing_idx: list[int] = []
        missing_chunks: list[Chunk] = []

        for i, chunk in enumerate(chunks):
            cached = await self._cache.get(self.model_id, chunk.content_hash)
            if cached is not None:
                slots[i] = EmbeddedChunk(
                    chunk=chunk,
                    embedding=cached,
                    embedding_model=self.model_id,
                    dimensions=self.dimensions,
                )
            else:
                missing_idx.append(i)
                missing_chunks.append(chunk)

        logger.debug(
            "CachedEmbedder: %d hits, %d misses (model=%s)",
            len(chunks) - len(missing_chunks),
            len(missing_chunks),
            self.model_id,
        )
        if missing_chunks:
            fresh = await self._inner.embed(missing_chunks)
            for idx, embedded in zip(missing_idx, fresh, strict=True):
                slots[idx] = embedded
                await self._cache.set(
                    self.model_id, embedded.chunk.content_hash, embedded.embedding
                )

        result: list[EmbeddedChunk] = []
        for slot in slots:
            assert slot is not None  # invariant: every slot filled by loops above
            result.append(slot)
        return result

    async def embed_query(self, query: str) -> list[float]:
        return await self._inner.embed_query(query)
