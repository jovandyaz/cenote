# SPDX-License-Identifier: Apache-2.0
"""Tests for TracedEmbedder / TracedRetriever / TracedReranker wrappers."""

from __future__ import annotations

from typing import Any

import pytest

from cenote.models import Chunk, EmbeddedChunk, RetrievalResult
from cenote.observability import NoopSpanContext, SpanContext
from cenote.observability.wrappers import (
    TracedEmbedder,
    TracedReranker,
    TracedRetriever,
)
from tests._factories import make_chunk, make_embedded, make_result
from tests._stubs import StubTracer


class _StubEmbedder:
    model_id = "mock:default"
    dimensions = 2

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [make_embedded(c.content, [0.1, 0.2], idx=i) for i, c in enumerate(chunks)]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2]


class _StubRetriever:
    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        return [
            make_result("a", 0.9, idx=0, retriever="stub"),
            make_result("b", 0.5, idx=1, retriever="stub"),
        ]


class _StubReranker:
    model_id = "mock:rerank"

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        return list(reversed(results))[:top_k] if top_k else list(reversed(results))


@pytest.mark.asyncio
class TestTracedEmbedder:
    async def test_passes_through_properties(self) -> None:
        wrapped = TracedEmbedder(_StubEmbedder(), StubTracer())
        assert wrapped.model_id == "mock:default"
        assert wrapped.dimensions == 2

    async def test_emits_span_on_embed(self) -> None:
        tracer = StubTracer()
        wrapped = TracedEmbedder(_StubEmbedder(), tracer)
        out = await wrapped.embed([make_chunk("hello", idx=0), make_chunk("world", idx=1)])
        assert len(out) == 2
        assert len(tracer.spans) == 1
        name, ctx = tracer.spans[0]
        assert name == "embedder.embed"
        assert ctx.attributes.get("gen_ai.request.model") == "mock:default"
        assert ctx.attributes.get("batch_size") == 2

    async def test_emits_span_on_embed_query(self) -> None:
        tracer = StubTracer()
        wrapped = TracedEmbedder(_StubEmbedder(), tracer)
        vec = await wrapped.embed_query("hola mundo")
        assert vec == [0.1, 0.2]
        assert len(tracer.spans) == 1
        name, ctx = tracer.spans[0]
        assert name == "embedder.embed_query"
        assert ctx.attributes.get("gen_ai.request.model") == "mock:default"


@pytest.mark.asyncio
class TestTracedRetriever:
    async def test_emits_span_with_attributes(self) -> None:
        tracer = StubTracer()
        wrapped = TracedRetriever(_StubRetriever(), tracer)
        out = await wrapped.retrieve("q", namespace="ns", limit=5)
        assert len(out) == 2
        name, ctx = tracer.spans[0]
        assert name == "retriever.retrieve"
        assert ctx.attributes.get("namespace") == "ns"
        assert ctx.attributes.get("limit") == 5
        assert ctx.attributes.get("result_count") == 2


@pytest.mark.asyncio
class TestTracedReranker:
    async def test_emits_span_and_passes_model_id(self) -> None:
        tracer = StubTracer()
        wrapped = TracedReranker(_StubReranker(), tracer)
        results = [
            make_result("a", 0.5, idx=0, retriever="stub"),
            make_result("b", 0.4, idx=1, retriever="stub"),
        ]
        out = await wrapped.rerank("q", results, top_k=1)
        assert wrapped.model_id == "mock:rerank"
        assert len(out) == 1
        name, ctx = tracer.spans[0]
        assert name == "reranker.rerank"
        assert ctx.attributes.get("gen_ai.request.model") == "mock:rerank"
        assert ctx.attributes.get("input_count") == 2
        assert ctx.attributes.get("top_k") == 1


@pytest.mark.asyncio
async def test_embedder_exception_recorded_and_reraised() -> None:
    class _BrokenEmbedder:
        model_id = "broken"
        dimensions = 2

        async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
            raise RuntimeError("network down")

        async def embed_query(self, query: str) -> list[float]:
            raise RuntimeError("network down")

    tracer = StubTracer()
    wrapped = TracedEmbedder(_BrokenEmbedder(), tracer)
    with pytest.raises(RuntimeError, match="network down"):
        await wrapped.embed([make_chunk("x")])
    _, ctx = tracer.spans[0]
    assert len(ctx.exceptions) == 1
    assert isinstance(ctx.exceptions[0], RuntimeError)


@pytest.mark.asyncio
async def test_retriever_exception_recorded_and_reraised() -> None:
    class _BrokenRetriever:
        async def retrieve(
            self,
            query: str,
            namespace: str,
            limit: int = 10,
            filter: dict[str, Any] | None = None,
        ) -> list[RetrievalResult]:
            raise RuntimeError("db down")

    tracer = StubTracer()
    wrapped = TracedRetriever(_BrokenRetriever(), tracer)
    with pytest.raises(RuntimeError, match="db down"):
        await wrapped.retrieve("q", namespace="ns")
    _, ctx = tracer.spans[0]
    assert len(ctx.exceptions) == 1
    assert isinstance(ctx.exceptions[0], RuntimeError)


@pytest.mark.asyncio
async def test_reranker_exception_recorded_and_reraised() -> None:
    class _BrokenReranker:
        model_id = "broken"

        async def rerank(
            self,
            query: str,
            results: list[RetrievalResult],
            top_k: int | None = None,
        ) -> list[RetrievalResult]:
            raise RuntimeError("api down")

    tracer = StubTracer()
    wrapped = TracedReranker(_BrokenReranker(), tracer)
    with pytest.raises(RuntimeError, match="api down"):
        await wrapped.rerank("q", [], top_k=5)
    _, ctx = tracer.spans[0]
    assert len(ctx.exceptions) == 1
    assert isinstance(ctx.exceptions[0], RuntimeError)


def test_noop_span_context_is_acceptable_spancontext_type() -> None:
    span: SpanContext = NoopSpanContext()
    span.set_attribute("k", "v")


@pytest.mark.asyncio
async def test_traced_vector_store_emits_search_span() -> None:
    """search() emits a 'store.search' span with namespace + limit + result_count."""
    from cenote.observability.wrappers import TracedVectorStore
    from cenote.stores.memory import InMemoryVectorStore

    inner = InMemoryVectorStore(dimensions=4)
    tracer = StubTracer()
    traced = TracedVectorStore(inner, tracer)

    results = await traced.search([0.1, 0.2, 0.3, 0.4], namespace="ns", limit=5)
    assert results == []

    span_names = [name for name, _ in tracer.spans]
    assert "store.search" in span_names
    (_, search_ctx) = next((n, c) for n, c in tracer.spans if n == "store.search")
    assert search_ctx.attributes["namespace"] == "ns"
    assert search_ctx.attributes["limit"] == 5
    assert search_ctx.attributes["result_count"] == 0


@pytest.mark.asyncio
async def test_traced_vector_store_emits_upsert_span() -> None:
    """upsert() emits a 'store.upsert' span with namespace + batch_size."""
    from cenote.observability.wrappers import TracedVectorStore
    from cenote.stores.memory import InMemoryVectorStore

    inner = InMemoryVectorStore(dimensions=4)
    tracer = StubTracer()
    traced = TracedVectorStore(inner, tracer)

    chunks = [
        EmbeddedChunk(
            chunk=Chunk(
                id=f"c{i}",
                document_id="d",
                content=f"t{i}",
                position=i,
                content_hash=f"h{i}",
            ),
            embedding=[0.1, 0.2, 0.3, 0.4],
            embedding_model="mock",
            dimensions=4,
        )
        for i in range(3)
    ]
    await traced.upsert(chunks, namespace="ns")

    upsert_ctx = next(c for n, c in tracer.spans if n == "store.upsert")
    assert upsert_ctx.attributes["namespace"] == "ns"
    assert upsert_ctx.attributes["batch_size"] == 3


@pytest.mark.asyncio
async def test_traced_vector_store_records_exception_on_failure() -> None:
    """Inner exception in search() is recorded on span before re-raising."""
    from cenote.observability.wrappers import TracedVectorStore

    class _BrokenStore:
        async def upsert(self, embedded_chunks: list[EmbeddedChunk], namespace: str) -> None:
            raise RuntimeError("nope")

        async def search(
            self,
            query_vector: list[float],
            namespace: str,
            limit: int = 10,
            filter: dict[str, Any] | None = None,
        ) -> list[RetrievalResult]:
            raise RuntimeError("nope")

        async def delete(self, chunk_ids: list[str], namespace: str) -> None:
            raise RuntimeError("nope")

        async def delete_namespace(self, namespace: str) -> None:
            raise RuntimeError("nope")

        async def get_all_chunks(self, namespace: str, filter: dict[str, Any] | None = None) -> Any:
            if False:
                yield
            raise RuntimeError("nope")

    tracer = StubTracer()
    traced = TracedVectorStore(_BrokenStore(), tracer)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        await traced.search([0.1] * 4, namespace="ns")

    search_ctx = next(c for n, c in tracer.spans if n == "store.search")
    assert len(search_ctx.exceptions) == 1
    assert isinstance(search_ctx.exceptions[0], RuntimeError)
