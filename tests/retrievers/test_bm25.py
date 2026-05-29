# SPDX-License-Identifier: Apache-2.0
"""Tests for BM25Retriever."""

from __future__ import annotations

import pytest

from cenote.models import Chunk
from cenote.retrievers import BM25Retriever
from cenote.stores import InMemoryVectorStore
from cenote.tokenizers import SpanishTokenizer
from tests._factories import make_embedded


@pytest.mark.asyncio
class TestBM25Retriever:
    async def test_returns_results_sorted_by_score(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        await store.upsert(
            [
                make_embedded("el perro corre rápido en el parque", [0.0, 0.0], idx=0),
                make_embedded("los gatos duermen mucho", [0.0, 0.0], idx=1),
                make_embedded("perro corriendo", [0.0, 0.0], idx=2),
            ],
            namespace="ns",
        )
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
        out = await retriever.retrieve("perros corriendo en el parque", namespace="ns", limit=3)
        assert len(out) >= 2
        assert out[0].score >= out[1].score
        cat = [r for r in out if "gatos" in r.chunk.content]
        if cat:
            assert all(r.score >= cat[0].score for r in out if "perro" in r.chunk.content)

    async def test_retriever_label_is_bm25(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        await store.upsert([make_embedded("perro corre", [0.0, 0.0], idx=0)], namespace="ns")
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
        out = await retriever.retrieve("perro", namespace="ns", limit=1)
        assert out[0].retriever == "bm25"

    async def test_namespace_isolation(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        await store.upsert([make_embedded("only-a", [0.0, 0.0], idx=0)], namespace="ns-a")
        await store.upsert([make_embedded("only-b", [0.0, 0.0], idx=0)], namespace="ns-b")
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
        out_a = await retriever.retrieve("only-a", namespace="ns-a", limit=2)
        assert all("only-b" not in r.chunk.content for r in out_a)

    async def test_empty_namespace_returns_empty(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
        out = await retriever.retrieve("perro", namespace="missing", limit=3)
        assert out == []

    async def test_from_chunks_constructor_skips_store(self) -> None:
        chunks = [
            Chunk(
                id="c1",
                document_id="d",
                content="el perro corre",
                position=0,
                content_hash="x",
            ),
            Chunk(
                id="c2",
                document_id="d",
                content="los gatos duermen",
                position=1,
                content_hash="y",
            ),
        ]
        retriever = BM25Retriever.from_chunks(chunks, tokenizer=SpanishTokenizer())
        out = await retriever.retrieve("perro corriendo", namespace="default", limit=2)
        assert out[0].chunk.id == "c1"

    async def test_metadata_filter(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        a = make_embedded("el perro corre", [0.0, 0.0], idx=0)
        b = make_embedded("el perro duerme", [0.0, 0.0], idx=1)
        a.chunk.metadata["lang"] = "es"
        b.chunk.metadata["lang"] = "en"
        await store.upsert([a, b], namespace="ns")
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
        out = await retriever.retrieve("perro", namespace="ns", limit=5, filter={"lang": "es"})
        assert len(out) == 1
        assert out[0].chunk.metadata["lang"] == "es"

    async def test_hyperparameters_k1_and_b_accepted(self) -> None:
        store = InMemoryVectorStore(dimensions=2)
        await store.upsert([make_embedded("perro corre", [0.0, 0.0], idx=0)], namespace="ns")
        retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer(), k1=1.2, b=0.5)
        out = await retriever.retrieve("perro", namespace="ns", limit=1)
        assert out[0].retriever == "bm25"


@pytest.mark.asyncio
async def test_bm25_invalidate_drops_cached_namespace() -> None:
    """invalidate(namespace) removes the cached BM25 index for that namespace."""
    chunks = [Chunk(id="c1", document_id="d", content="hola mundo", position=0, content_hash="h")]
    r = BM25Retriever.from_chunks(chunks, tokenizer=SpanishTokenizer(), namespace="x")
    assert "x" in r._caches
    r.invalidate("x")
    assert "x" not in r._caches


@pytest.mark.asyncio
async def test_bm25_invalidate_unknown_namespace_is_noop() -> None:
    """invalidate() on a never-cached namespace is a silent no-op (does not raise)."""
    r = BM25Retriever(store=None, tokenizer=SpanishTokenizer())
    r.invalidate("never-cached")
    assert "never-cached" not in r._caches


@pytest.mark.asyncio
async def test_bm25_lru_evicts_oldest_when_over_capacity() -> None:
    """When the (N+1)-th namespace is queried, the least-recently-used is evicted."""
    store = InMemoryVectorStore(dimensions=4)
    for ns in ("a", "b", "c"):
        await store.upsert(
            [make_embedded("hola mundo", [0.1, 0.2, 0.3, 0.4], idx=0, document_id=ns)],
            namespace=ns,
        )

    r = BM25Retriever(
        store=store,
        tokenizer=SpanishTokenizer(),
        max_cached_namespaces=2,
    )
    await r.retrieve("hola", namespace="a")
    await r.retrieve("hola", namespace="b")
    assert set(r._caches.keys()) == {"a", "b"}
    await r.retrieve("hola", namespace="c")
    assert set(r._caches.keys()) == {"b", "c"}


@pytest.mark.asyncio
async def test_bm25_lru_move_to_end_on_hit() -> None:
    """Re-accessing a cached namespace moves it to most-recently-used position."""
    chunks_a = [Chunk(id="a:0", document_id="a", content="hola", position=0, content_hash="ha")]
    chunks_b = [Chunk(id="b:0", document_id="b", content="hola", position=0, content_hash="hb")]
    r = BM25Retriever.from_chunks(chunks_a, tokenizer=SpanishTokenizer(), namespace="a")
    r._caches["b"] = r._build_index(chunks_b)
    await r.retrieve("hola", namespace="a")
    assert list(r._caches.keys()) == ["b", "a"]


def test_bm25_rejects_zero_max_cached() -> None:
    """ConfigurationError is raised when max_cached_namespaces is non-positive."""
    from cenote.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        BM25Retriever(store=None, tokenizer=SpanishTokenizer(), max_cached_namespaces=0)
