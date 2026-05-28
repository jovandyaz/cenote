# SPDX-License-Identifier: Apache-2.0
"""Traced wrappers — opt-in tracing for any Embedder/Retriever/Reranker impl."""

from __future__ import annotations

from typing import Any

from cenote.embedders.base import Embedder
from cenote.models import Chunk, EmbeddedChunk, RetrievalResult
from cenote.observability.base import Tracer
from cenote.rerankers.base import Reranker
from cenote.retrievers.base import Retriever


class TracedEmbedder:
    """Wraps any Embedder with span emission via the given Tracer."""

    def __init__(self, inner: Embedder, tracer: Tracer) -> None:
        self._inner = inner
        self._tracer = tracer

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        async with self._tracer.span("embedder.embed") as span:
            span.set_attribute("gen_ai.request.model", self._inner.model_id)
            span.set_attribute("batch_size", len(chunks))
            try:
                return await self._inner.embed(chunks)
            except Exception as exc:
                span.record_exception(exc)
                raise

    async def embed_query(self, query: str) -> list[float]:
        async with self._tracer.span("embedder.embed_query") as span:
            span.set_attribute("gen_ai.request.model", self._inner.model_id)
            try:
                return await self._inner.embed_query(query)
            except Exception as exc:
                span.record_exception(exc)
                raise


class TracedRetriever:
    """Wraps any Retriever with span emission via the given Tracer."""

    def __init__(self, inner: Retriever, tracer: Tracer) -> None:
        self._inner = inner
        self._tracer = tracer

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        async with self._tracer.span("retriever.retrieve") as span:
            span.set_attribute("namespace", namespace)
            span.set_attribute("limit", limit)
            try:
                results = await self._inner.retrieve(
                    query, namespace=namespace, limit=limit, filter=filter
                )
            except Exception as exc:
                span.record_exception(exc)
                raise
            span.set_attribute("result_count", len(results))
            return results


class TracedReranker:
    """Wraps any Reranker with span emission via the given Tracer."""

    def __init__(self, inner: Reranker, tracer: Tracer) -> None:
        self._inner = inner
        self._tracer = tracer

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        async with self._tracer.span("reranker.rerank") as span:
            span.set_attribute("gen_ai.request.model", self._inner.model_id)
            span.set_attribute("input_count", len(results))
            if top_k is not None:
                span.set_attribute("top_k", top_k)
            try:
                return await self._inner.rerank(query, results, top_k=top_k)
            except Exception as exc:
                span.record_exception(exc)
                raise


__all__ = ["TracedEmbedder", "TracedReranker", "TracedRetriever"]
