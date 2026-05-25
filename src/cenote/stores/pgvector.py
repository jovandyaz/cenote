# SPDX-License-Identifier: Apache-2.0
"""PgVectorStore — async Postgres + pgvector backend (production-hardened)."""

from __future__ import annotations

import asyncio
import json
import logging
from importlib import resources
from typing import Any

import asyncpg

from cenote.errors import ConfigurationError, DimensionMismatchError
from cenote.models import Chunk, EmbeddedChunk, RetrievalResult

logger = logging.getLogger(__name__)


class PgVectorStore:
    """Production-grade VectorStore backed by Postgres + pgvector.

    Multi-tenant via the `namespace` column. Cosine similarity via the `<=>` operator.
    Dimensions are fixed at construction; do not mix dimensions in one store instance.
    """

    def __init__(
        self,
        pool: asyncpg.Pool[asyncpg.Record],
        dimensions: int,
        *,
        table_name: str = "cenote_chunks",
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
        hnsw_ef_search: int | None = None,
    ) -> None:
        if dimensions <= 0:
            raise ConfigurationError("dimensions must be positive")
        if hnsw_m <= 0:
            raise ConfigurationError("hnsw_m must be positive")
        if hnsw_ef_construction <= 0:
            raise ConfigurationError("hnsw_ef_construction must be positive")
        self._pool = pool
        self._dimensions = dimensions
        self._table = table_name
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construction = hnsw_ef_construction
        self._hnsw_ef_search = hnsw_ef_search

    @classmethod
    async def connect(
        cls,
        dsn: str,
        dimensions: int,
        *,
        min_size: int = 1,
        max_size: int = 10,
        startup_retries: int = 5,
        startup_backoff_seconds: float = 1.0,
        **store_kwargs: Any,
    ) -> PgVectorStore:
        """Create a connection pool with exponential-backoff retry on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(startup_retries + 1):
            try:
                pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
                assert pool is not None
                logger.info("PgVectorStore connected (attempt %d)", attempt + 1)
                return cls(pool=pool, dimensions=dimensions, **store_kwargs)
            except (OSError, asyncpg.PostgresError) as exc:
                last_exc = exc
                if attempt == startup_retries:
                    break
                wait = startup_backoff_seconds * (2**attempt)
                logger.warning(
                    "PgVectorStore connect failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    startup_retries + 1,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)
        assert last_exc is not None
        raise last_exc

    async def apply_migrations(self) -> None:
        """Apply pending SQL migrations idempotently via a tracking table."""
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS cenote_schema_migrations (
                        version    TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
            )
            applied = {
                r["version"]
                for r in await conn.fetch("SELECT version FROM cenote_schema_migrations")
            }
            for name in self._migration_files():
                if name in applied:
                    continue
                sql = (
                    self._read_migration(name)
                    .replace("{DIMENSIONS}", str(self._dimensions))
                    .replace("{HNSW_M}", str(self._hnsw_m))
                    .replace("{HNSW_EF_CONSTRUCTION}", str(self._hnsw_ef_construction))
                )
                logger.info("Applying migration %s", name)
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO cenote_schema_migrations (version) VALUES ($1)", name
                )

    async def upsert(self, embedded_chunks: list[EmbeddedChunk], namespace: str) -> None:
        """Insert or update embedded chunks. Validates dimensions before any SQL."""
        if not embedded_chunks:
            return
        for ec in embedded_chunks:
            if len(ec.embedding) != self._dimensions:
                raise DimensionMismatchError(
                    f"embedding dim {len(ec.embedding)} != store dim "
                    f"{self._dimensions} (chunk id={ec.chunk.id})"
                )
        rows = [
            (
                ec.chunk.id,
                namespace,
                ec.chunk.document_id,
                ec.chunk.content,
                ec.chunk.position,
                json.dumps(ec.chunk.metadata),
                ec.chunk.content_hash,
                _vector_literal(ec.embedding),
                ec.embedding_model,
            )
            for ec in embedded_chunks
        ]
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.executemany(
                f"""
                    INSERT INTO {self._table}
                        (id, namespace, document_id, content, position, metadata,
                         content_hash, embedding, embedding_model)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::vector, $9)
                    ON CONFLICT (namespace, id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        content = EXCLUDED.content,
                        position = EXCLUDED.position,
                        metadata = EXCLUDED.metadata,
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        embedding_model = EXCLUDED.embedding_model
                    """,
                rows,
            )

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
        params: list[Any] = [namespace, _vector_literal(query_vector), limit]
        filter_sql = ""
        if filter:
            params.append(json.dumps(filter))
            filter_sql = "AND metadata @> $4::jsonb "
        sql = f"""
            SELECT id, document_id, content, position, metadata, content_hash,
                   1 - (embedding <=> $2::vector) AS score
            FROM {self._table}
            WHERE namespace = $1 {filter_sql}
            ORDER BY embedding <=> $2::vector
            LIMIT $3
        """
        async with self._pool.acquire() as conn:
            if self._hnsw_ef_search is not None:
                await conn.execute(f"SET LOCAL hnsw.ef_search = {int(self._hnsw_ef_search)}")
            rows = await conn.fetch(sql, *params)
        return [
            RetrievalResult(
                chunk=Chunk(
                    id=r["id"],
                    document_id=r["document_id"],
                    content=r["content"],
                    position=r["position"],
                    metadata=(
                        json.loads(r["metadata"])
                        if isinstance(r["metadata"], str)
                        else r["metadata"]
                    ),
                    content_hash=r["content_hash"],
                ),
                score=float(r["score"]),
                retriever="vector",
            )
            for r in rows
        ]

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        if not chunk_ids:
            return
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                f"DELETE FROM {self._table} WHERE namespace = $1 AND id = ANY($2)",
                namespace,
                chunk_ids,
            )

    async def delete_namespace(self, namespace: str) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(f"DELETE FROM {self._table} WHERE namespace = $1", namespace)

    async def close(self) -> None:
        await self._pool.close()

    @staticmethod
    def _migration_files() -> list[str]:
        """Return migration filenames in lexicographic order."""
        return sorted(
            f.name
            for f in resources.files("cenote.stores.pgvector_migrations").iterdir()
            if f.name.endswith(".sql")
        )

    @staticmethod
    def _read_migration(name: str) -> str:
        with (
            resources.files("cenote.stores.pgvector_migrations")
            .joinpath(name)
            .open("r", encoding="utf-8") as fh
        ):
            return fh.read()


def _vector_literal(vector: list[float]) -> str:
    """Serialize a Python list to the `[v1,v2,...]` literal pgvector expects."""
    return "[" + ",".join(repr(x) for x in vector) + "]"
