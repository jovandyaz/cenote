"""Integration tests for PgVectorStore. Requires Postgres at TEST_DATABASE_URL."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from importlib import resources

import pytest
import pytest_asyncio

from cenote.errors import DimensionMismatchError
from cenote.stores import PgVectorStore
from tests._factories import make_embedded as _embedded


def _expected_migrations() -> list[str]:
    return sorted(
        f.name
        for f in resources.files("cenote.stores.pgvector_migrations").iterdir()
        if f.name.endswith(".sql")
    )


pytestmark = pytest.mark.integration

DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://cenote:cenote@localhost:5433/cenote_test",
)


@pytest_asyncio.fixture
async def store() -> AsyncGenerator[PgVectorStore, None]:
    s = await PgVectorStore.connect(DSN, dimensions=4)
    await s.apply_migrations()
    yield s
    await s.close()


@pytest.fixture
def ns() -> str:
    return f"test-{uuid.uuid4()}"


@pytest.mark.asyncio
class TestPgVectorStore:
    async def test_upsert_and_search_roundtrip(self, store: PgVectorStore, ns: str) -> None:
        items = [
            _embedded("hello", [1.0, 0.0, 0.0, 0.0], idx=0),
            _embedded("world", [0.0, 1.0, 0.0, 0.0], idx=1),
        ]
        await store.upsert(items, namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns, limit=2)
        assert {r.chunk.content for r in out} == {"hello", "world"}
        assert out[0].chunk.content == "hello"

    async def test_namespace_isolation(self, store: PgVectorStore) -> None:
        ns_a = f"a-{uuid.uuid4()}"
        ns_b = f"b-{uuid.uuid4()}"
        await store.upsert([_embedded("only-a", [1.0, 0.0, 0.0, 0.0])], namespace=ns_a)
        await store.upsert([_embedded("only-b", [1.0, 0.0, 0.0, 0.0])], namespace=ns_b)
        out_a = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns_a)
        out_b = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns_b)
        assert {r.chunk.content for r in out_a} == {"only-a"}
        assert {r.chunk.content for r in out_b} == {"only-b"}
        await store.delete_namespace(ns_a)
        await store.delete_namespace(ns_b)

    async def test_metadata_filter(self, store: PgVectorStore, ns: str) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta", [1.0, 0.0, 0.0, 0.0], idx=1)
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace=ns)
        out_es = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns, filter={"lang": "es"})
        assert {r.chunk.content for r in out_es} == {"beta"}

    async def test_delete_single(self, store: PgVectorStore, ns: str) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta", [0.0, 1.0, 0.0, 0.0], idx=1)
        await store.upsert([a, b], namespace=ns)
        await store.delete([a.chunk.id], namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert "alpha" not in {r.chunk.content for r in out}

    async def test_idempotent_upsert(self, store: PgVectorStore, ns: str) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        await store.upsert([a, a], namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert len([r for r in out if r.chunk.content == "alpha"]) == 1

    async def test_apply_migrations_is_idempotent(self, store: PgVectorStore) -> None:
        """Running apply_migrations twice must not error and not duplicate work."""
        await store.apply_migrations()  # already applied by fixture; this is the 2nd run
        async with store._pool.acquire() as conn:
            rows = await conn.fetch("SELECT version FROM cenote_schema_migrations ORDER BY version")
        versions = [r["version"] for r in rows]
        assert versions == _expected_migrations()

    async def test_dimension_mismatch_raises_clear_error(
        self, store: PgVectorStore, ns: str
    ) -> None:
        bad = _embedded("oops", [1.0, 0.0])  # store dim is 4
        with pytest.raises(DimensionMismatchError, match=r"dim .* != store dim"):
            await store.upsert([bad], namespace=ns)

    async def test_transaction_rollback_on_partial_failure(
        self, store: PgVectorStore, ns: str
    ) -> None:
        """Dim mismatch caught before any SQL — nothing is inserted."""
        good = _embedded("good", [1.0, 0.0, 0.0, 0.0], idx=0)
        bad = _embedded("bad", [1.0, 0.0])  # dim 2 vs store dim 4
        with pytest.raises(DimensionMismatchError):
            await store.upsert([good, bad], namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert {r.chunk.content for r in out} == set()

    async def test_get_all_chunks_yields_paginated(self, store: PgVectorStore, ns: str) -> None:
        items = [_embedded(f"text-{i}", [1.0, 0.0, 0.0, 0.0], idx=i) for i in range(150)]
        await store.upsert(items, namespace=ns)
        out = [c async for c in store.get_all_chunks(namespace=ns)]
        assert len(out) == 150
        assert {c.content for c in out} == {f"text-{i}" for i in range(150)}

    async def test_get_all_chunks_namespace_isolation(self, store: PgVectorStore) -> None:
        ns_a = f"a-{uuid.uuid4()}"
        ns_b = f"b-{uuid.uuid4()}"
        await store.upsert([_embedded("only-a", [1.0, 0.0, 0.0, 0.0])], namespace=ns_a)
        await store.upsert([_embedded("only-b", [1.0, 0.0, 0.0, 0.0])], namespace=ns_b)
        a_out = [c async for c in store.get_all_chunks(namespace=ns_a)]
        assert {c.content for c in a_out} == {"only-a"}
        await store.delete_namespace(ns_a)
        await store.delete_namespace(ns_b)

    async def test_get_all_chunks_filter(self, store: PgVectorStore, ns: str) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta", [1.0, 0.0, 0.0, 0.0], idx=1)
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace=ns)
        out = [c async for c in store.get_all_chunks(namespace=ns, filter={"lang": "es"})]
        assert [c.content for c in out] == ["beta"]


@pytest.mark.asyncio
async def test_hnsw_ef_search_executes_within_transaction() -> None:
    """Sentinel for the SET LOCAL transaction-wrap fix.

    PostgreSQL silently discards `SET LOCAL` outside a transaction.
    Before the fix, calling search() with `hnsw_ef_search` set would NOT
    actually apply the setting. After the fix, the SET LOCAL runs inside
    `conn.transaction()` and takes effect.

    This test asserts the call path completes without error when
    `hnsw_ef_search` is set — that the SET LOCAL is in a valid transaction
    context and doesn't raise. Validating the actual recall improvement
    requires a real HNSW corpus and is left to manual benchmarking.
    """
    store = await PgVectorStore.connect(DSN, dimensions=4, hnsw_ef_search=99)
    try:
        await store.apply_migrations()
        result = await store.search([0.1, 0.2, 0.3, 0.4], namespace="t_ef_search", limit=1)
        assert result == []
    finally:
        await store.close()
