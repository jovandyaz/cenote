# SPDX-License-Identifier: Apache-2.0
"""Caching wrapper around any Embedder."""

from __future__ import annotations

import logging
import struct
from pathlib import Path
from typing import Protocol

import aiosqlite

from cenote.embedders.base import Embedder
from cenote.models import Chunk, EmbeddedChunk
from cenote.types import Vector

logger = logging.getLogger(__name__)


class EmbeddingCache(Protocol):
    """Async key-value store for embedding vectors, keyed by (model_id, content_hash)."""

    async def get(self, model_id: str, content_hash: str) -> Vector | None: ...

    async def set(self, model_id: str, content_hash: str, embedding: Vector) -> None: ...

    async def set_many(self, items: list[tuple[str, str, Vector]]) -> None:
        """Bulk write — single transaction in persistent backends.

        `items` is a list of `(model_id, content_hash, embedding)` tuples.
        """
        ...


class InMemoryCache:
    """Dict-backed EmbeddingCache. Suitable for tests and small workloads."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], Vector] = {}

    async def get(self, model_id: str, content_hash: str) -> Vector | None:
        return self._store.get((model_id, content_hash))

    async def set(self, model_id: str, content_hash: str, embedding: Vector) -> None:
        # Store a copy so external mutation of the caller's list cannot poison the cache.
        self._store[(model_id, content_hash)] = list(embedding)

    async def set_many(self, items: list[tuple[str, str, Vector]]) -> None:
        for model_id, content_hash, embedding in items:
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
            await self._cache.set_many(
                [(self.model_id, ec.chunk.content_hash, ec.embedding) for ec in fresh]
            )

        result: list[EmbeddedChunk] = []
        for slot in slots:
            assert slot is not None  # invariant: every slot filled by loops above
            result.append(slot)
        return result

    async def embed_query(self, query: str) -> list[float]:
        return await self._inner.embed_query(query)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cenote_embedding_cache (
    cache_key  TEXT    PRIMARY KEY,
    dimensions INTEGER NOT NULL,
    vector     BLOB    NOT NULL,
    created_at REAL    NOT NULL DEFAULT (julianday('now'))
);
"""


class SqliteCache:
    """SQLite-backed EmbeddingCache. Vectors stored as float32 BLOBs.

    Storage is intentionally float32; rounding error is well below cosine
    similarity noise for retrieval. WAL mode is enabled at connect for ~10x
    batch-write throughput. Single-process-safe via SQLite's file lock;
    concurrent tasks on one connection are serialized by aiosqlite.

    Dimension consistency across overwrites is the caller's responsibility:
    storing two different-dimension vectors under the same `(model_id,
    content_hash)` will silently replace the previous one.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @classmethod
    async def connect(cls, path: str | Path) -> SqliteCache:
        """Open the cache file (created if absent), enable WAL, apply schema."""
        conn = await aiosqlite.connect(str(path))
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.executescript(_SCHEMA)
        await conn.commit()
        return cls(conn)

    async def __aenter__(self) -> SqliteCache:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._conn.close()

    async def get(self, model_id: str, content_hash: str) -> Vector | None:
        key = f"{model_id}:{content_hash}"
        async with self._conn.execute(
            "SELECT dimensions, vector FROM cenote_embedding_cache WHERE cache_key = ?",
            (key,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        dimensions, blob = row
        return list(struct.unpack(f"{int(dimensions)}f", blob))

    async def set(self, model_id: str, content_hash: str, embedding: Vector) -> None:
        await self.set_many([(model_id, content_hash, embedding)])

    async def set_many(self, items: list[tuple[str, str, Vector]]) -> None:
        if not items:
            return
        rows = [
            (
                f"{model_id}:{content_hash}",
                len(embedding),
                struct.pack(f"{len(embedding)}f", *embedding),
            )
            for model_id, content_hash, embedding in items
        ]
        async with self._conn.executemany(
            "INSERT OR REPLACE INTO cenote_embedding_cache "
            "(cache_key, dimensions, vector) VALUES (?, ?, ?)",
            rows,
        ):
            pass
        await self._conn.commit()
