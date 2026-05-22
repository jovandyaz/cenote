"""Tests for cenote.embedders.cache."""

from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.embedders.cache import CachedEmbedder, InMemoryCache
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
