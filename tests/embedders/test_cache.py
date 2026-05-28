"""Tests for cenote.embedders.cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cenote.embedders import MockEmbedder
from cenote.embedders.cache import CachedEmbedder, InMemoryCache, SqliteCache
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


class _CountingEmbedder(MockEmbedder):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions, model_name="counting")
        self.calls = 0
        self.chunks_seen = 0

    async def embed(self, chunks):
        self.calls += 1
        self.chunks_seen += len(chunks)
        return await super().embed(chunks)


@pytest.mark.asyncio
class TestInMemoryCache:
    async def test_get_miss_returns_none(self) -> None:
        cache = InMemoryCache()
        assert await cache.get("mock:default", "abc") is None

    async def test_set_then_get_returns_value(self) -> None:
        cache = InMemoryCache()
        await cache.set("mock:default", "abc", [1.0, 2.0])
        assert await cache.get("mock:default", "abc") == [1.0, 2.0]

    async def test_keys_distinguish_model_ids(self) -> None:
        cache = InMemoryCache()
        await cache.set("voyage:voyage-3", "h", [1.0])
        await cache.set("cohere:embed-multilingual-v3", "h", [2.0])
        assert await cache.get("voyage:voyage-3", "h") == [1.0]
        assert await cache.get("cohere:embed-multilingual-v3", "h") == [2.0]

    async def test_set_many_writes_all_items(self) -> None:
        cache = InMemoryCache()
        await cache.set_many(
            [
                ("m", "h0", [1.0, 2.0]),
                ("m", "h1", [3.0, 4.0]),
                ("m", "h2", [5.0, 6.0]),
            ]
        )
        assert await cache.get("m", "h0") == [1.0, 2.0]
        assert await cache.get("m", "h1") == [3.0, 4.0]
        assert await cache.get("m", "h2") == [5.0, 6.0]

    async def test_set_many_empty_is_noop(self) -> None:
        cache = InMemoryCache()
        await cache.set_many([])
        assert await cache.get("m", "h") is None


@pytest.mark.asyncio
class TestCachedEmbedder:
    async def test_passthrough_when_cache_empty(self) -> None:
        inner = _CountingEmbedder()
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        chunks = [_chunk("hello"), _chunk("world", idx=1)]
        out = await wrapped.embed(chunks)
        assert len(out) == 2
        assert inner.calls == 1
        assert inner.chunks_seen == 2

    async def test_full_hit_skips_inner(self) -> None:
        inner = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped = CachedEmbedder(inner=inner, cache=cache)
        chunks = [_chunk("hello"), _chunk("world", idx=1)]
        await wrapped.embed(chunks)
        # Second pass with the same chunks → no inner calls
        inner.calls = 0
        inner.chunks_seen = 0
        await wrapped.embed(chunks)
        assert inner.calls == 0
        assert inner.chunks_seen == 0

    async def test_mixed_batch_preserves_order(self) -> None:
        inner = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped = CachedEmbedder(inner=inner, cache=cache)
        # Pre-warm cache for "B" only.
        await wrapped.embed([_chunk("B")])
        inner.calls = 0
        inner.chunks_seen = 0
        batch = [_chunk("A", 0), _chunk("B", 1), _chunk("C", 2)]
        result = await wrapped.embed(batch)
        # Only A and C must hit the inner embedder.
        assert inner.chunks_seen == 2
        assert [r.chunk.content for r in result] == ["A", "B", "C"]

    async def test_forwards_model_id_and_dimensions(self) -> None:
        inner = _CountingEmbedder(dimensions=32)
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        assert wrapped.model_id == inner.model_id
        assert wrapped.dimensions == 32

    async def test_query_passthrough(self) -> None:
        inner = _CountingEmbedder()
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        v = await wrapped.embed_query("hello")
        assert len(v) == 8  # default _CountingEmbedder dimensions

    async def test_different_model_ids_dont_collide(self) -> None:
        inner_a = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped_a = CachedEmbedder(inner=inner_a, cache=cache)
        await wrapped_a.embed([_chunk("x")])  # populates "mock:counting" key

        # Different inner model_id reuses the same cache instance.
        class _OtherEmbedder(_CountingEmbedder):
            @property
            def model_id(self) -> str:
                return "mock:other"

        inner_b = _OtherEmbedder()
        wrapped_b = CachedEmbedder(inner=inner_b, cache=cache)
        inner_b.calls = 0
        await wrapped_b.embed([_chunk("x")])  # must miss
        assert inner_b.calls == 1


@pytest.mark.asyncio
class TestSqliteCache:
    async def test_round_trip_get_set(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        await cache.set("voyage:voyage-3", "abc123", [0.1, 0.2, 0.3, 0.4])
        out = await cache.get("voyage:voyage-3", "abc123")
        assert out is not None
        assert len(out) == 4
        assert out == pytest.approx([0.1, 0.2, 0.3, 0.4], rel=1e-6)
        await cache.close()

    async def test_persistence_across_reopen(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        cache_a = await SqliteCache.connect(path)
        await cache_a.set("voyage:voyage-3", "abc123", [1.0, 2.0, 3.0])
        await cache_a.close()

        cache_b = await SqliteCache.connect(path)
        out = await cache_b.get("voyage:voyage-3", "abc123")
        assert out == pytest.approx([1.0, 2.0, 3.0], rel=1e-6)
        await cache_b.close()

    async def test_missing_key_returns_none(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        assert await cache.get("voyage:voyage-3", "never-set") is None
        await cache.close()

    async def test_different_models_isolate_same_content_hash(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        await cache.set("voyage:voyage-3", "shared-hash", [1.0, 2.0])
        await cache.set("cohere:embed-multilingual-v3.0", "shared-hash", [3.0, 4.0])
        a = await cache.get("voyage:voyage-3", "shared-hash")
        b = await cache.get("cohere:embed-multilingual-v3.0", "shared-hash")
        assert a == pytest.approx([1.0, 2.0])
        assert b == pytest.approx([3.0, 4.0])
        await cache.close()

    async def test_schema_idempotent(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        cache_a = await SqliteCache.connect(path)
        await cache_a.close()
        cache_b = await SqliteCache.connect(path)
        await cache_b.close()

    async def test_overwrite_same_key(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        await cache.set("m", "h", [1.0, 2.0])
        await cache.set("m", "h", [9.0, 8.0])
        out = await cache.get("m", "h")
        assert out == pytest.approx([9.0, 8.0])
        await cache.close()

    async def test_works_with_cached_embedder(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        inner = _CountingEmbedder(dimensions=8)
        wrapped = CachedEmbedder(inner=inner, cache=cache)
        chunks = [
            Chunk(id="d:0", document_id="d", content="hola", position=0, content_hash="h1"),
            Chunk(id="d:1", document_id="d", content="mundo", position=1, content_hash="h2"),
        ]
        first = await wrapped.embed(chunks)
        assert inner.chunks_seen == 2  # first pass: all miss
        inner.calls = 0
        inner.chunks_seen = 0
        second = await wrapped.embed(chunks)
        assert inner.chunks_seen == 0  # second pass: all hit (SQLite persistence)
        assert first[0].embedding == pytest.approx(second[0].embedding, rel=1e-6)
        assert first[1].embedding == pytest.approx(second[1].embedding, rel=1e-6)
        await cache.close()

    async def test_async_context_manager_closes_connection(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        async with await SqliteCache.connect(path) as cache:
            await cache.set("m", "h", [1.0, 2.0])
        async with await SqliteCache.connect(path) as cache:
            out = await cache.get("m", "h")
            assert out == pytest.approx([1.0, 2.0])

    async def test_set_many_bulk_write(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        items = [("m", f"h{i}", [float(i), float(i + 1)]) for i in range(20)]
        await cache.set_many(items)
        for i in range(20):
            out = await cache.get("m", f"h{i}")
            assert out == pytest.approx([float(i), float(i + 1)])
        await cache.close()

    async def test_set_many_empty_is_noop(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        await cache.set_many([])
        await cache.close()

    async def test_concurrent_sets_are_serialized(self, tmp_path: Path) -> None:
        import asyncio

        cache = await SqliteCache.connect(tmp_path / "cache.db")
        await asyncio.gather(
            *[cache.set("m", f"h{i}", [float(i), float(i + 1)]) for i in range(50)]
        )
        for i in range(50):
            out = await cache.get("m", f"h{i}")
            assert out == pytest.approx([float(i), float(i + 1)])
        await cache.close()

    async def test_handles_realistic_dimension(self, tmp_path: Path) -> None:
        cache = await SqliteCache.connect(tmp_path / "cache.db")
        vec = [float(i) * 0.001 for i in range(1024)]
        await cache.set("voyage:voyage-3", "h", vec)
        out = await cache.get("voyage:voyage-3", "h")
        assert out is not None
        assert len(out) == 1024
        assert out == pytest.approx(vec, rel=1e-5)
        await cache.close()
