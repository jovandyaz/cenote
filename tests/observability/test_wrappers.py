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


class _StubSpanContext:
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.exceptions: list[BaseException] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(exception)


class _StubTracer:
    def __init__(self) -> None:
        self.spans: list[tuple[str, _StubSpanContext]] = []

    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        ctx = _StubSpanContext()
        if attributes:
            ctx.attributes.update(attributes)
        self.spans.append((name, ctx))
        return _AsyncCtx(ctx)


class _AsyncCtx:
    def __init__(self, ctx: _StubSpanContext) -> None:
        self._ctx = ctx

    async def __aenter__(self) -> _StubSpanContext:
        return self._ctx

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


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
        wrapped = TracedEmbedder(_StubEmbedder(), _StubTracer())
        assert wrapped.model_id == "mock:default"
        assert wrapped.dimensions == 2

    async def test_emits_span_on_embed(self) -> None:
        tracer = _StubTracer()
        wrapped = TracedEmbedder(_StubEmbedder(), tracer)
        out = await wrapped.embed([make_chunk("hello", idx=0), make_chunk("world", idx=1)])
        assert len(out) == 2
        assert len(tracer.spans) == 1
        name, ctx = tracer.spans[0]
        assert name == "embedder.embed"
        assert ctx.attributes.get("gen_ai.request.model") == "mock:default"
        assert ctx.attributes.get("batch_size") == 2

    async def test_emits_span_on_embed_query(self) -> None:
        tracer = _StubTracer()
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
        tracer = _StubTracer()
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
        tracer = _StubTracer()
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

    tracer = _StubTracer()
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

    tracer = _StubTracer()
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

    tracer = _StubTracer()
    wrapped = TracedReranker(_BrokenReranker(), tracer)
    with pytest.raises(RuntimeError, match="api down"):
        await wrapped.rerank("q", [], top_k=5)
    _, ctx = tracer.spans[0]
    assert len(ctx.exceptions) == 1
    assert isinstance(ctx.exceptions[0], RuntimeError)


def test_noop_span_context_is_acceptable_spancontext_type() -> None:
    span: SpanContext = NoopSpanContext()
    span.set_attribute("k", "v")
