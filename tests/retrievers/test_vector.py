"""Tests for VectorRetriever."""

from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.models import Chunk
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore


def _chunk(text: str, idx: int = 0, *, doc: str = "d") -> Chunk:
    return Chunk(
        id=f"{doc}:{idx}",
        document_id=doc,
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


@pytest.fixture
async def populated_store() -> InMemoryVectorStore:
    embedder = MockEmbedder(dimensions=64)
    chunks = [
        _chunk(t, i)
        for i, t in enumerate(
            [
                "the dog chased the cat",
                "machine learning is fun",
                "neural networks learn patterns",
                "the cat slept on the mat",
                "transformers process tokens",
            ]
        )
    ]
    embedded = await embedder.embed(chunks)
    store = InMemoryVectorStore(dimensions=64)
    await store.upsert(embedded, namespace="ns")
    return store


@pytest.mark.asyncio
class TestVectorRetriever:
    async def test_retrieves_sorted_results(self, populated_store: InMemoryVectorStore) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        results = await retriever.retrieve("the cat", namespace="ns", limit=3)
        assert len(results) == 3
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
        assert all(r.retriever == "vector" for r in results)

    async def test_namespace_isolation(self, populated_store: InMemoryVectorStore) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        out_other = await retriever.retrieve("anything", namespace="other-ns", limit=5)
        assert out_other == []

    async def test_limit_is_respected(self, populated_store: InMemoryVectorStore) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        results = await retriever.retrieve("anything", namespace="ns", limit=2)
        assert len(results) == 2

    async def test_filter_passed_through(self) -> None:
        embedder = MockEmbedder(dimensions=16)
        store = InMemoryVectorStore(dimensions=16)
        a = _chunk("alpha", 0)
        a.metadata["lang"] = "en"
        b = _chunk("beta", 1)
        b.metadata["lang"] = "es"
        embedded = await embedder.embed([a, b])
        await store.upsert(embedded, namespace="ns")
        retriever = VectorRetriever(embedder=embedder, store=store)
        out = await retriever.retrieve("anything", namespace="ns", limit=5, filter={"lang": "es"})
        assert {r.chunk.content for r in out} == {"beta"}
