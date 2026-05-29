# SPDX-License-Identifier: Apache-2.0
"""Traced wrappers — opt-in tracing for any Embedder/Retriever/Reranker impl."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from cenote.embedders.base import Embedder
from cenote.models import Chunk, EmbeddedChunk, RetrievalResult
from cenote.observability.base import Tracer
from cenote.rerankers.base import Reranker
from cenote.retrievers.base import Retriever
from cenote.stores.base import VectorStore
from cenote.types import Vector


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


class TracedVectorStore:
    """Wraps any VectorStore with span emission via the given Tracer.

    Mirrors TracedEmbedder/TracedRetriever pattern. `get_all_chunks` is NOT
    wrapped — it returns an async iterator, and span lifetime would conflict
    with caller-driven iteration. Trace per-chunk consumption from the caller
    if needed.
    """

    def __init__(self, inner: VectorStore, tracer: Tracer) -> None:
        self._inner = inner
        self._tracer = tracer

    async def upsert(
        self,
        embedded_chunks: list[EmbeddedChunk],
        namespace: str,
    ) -> None:
        async with self._tracer.span("store.upsert") as span:
            span.set_attribute("namespace", namespace)
            span.set_attribute("batch_size", len(embedded_chunks))
            try:
                await self._inner.upsert(embedded_chunks, namespace=namespace)
            except Exception as exc:
                span.record_exception(exc)
                raise

    async def search(
        self,
        query_vector: Vector,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        async with self._tracer.span("store.search") as span:
            span.set_attribute("namespace", namespace)
            span.set_attribute("limit", limit)
            try:
                results = await self._inner.search(
                    query_vector, namespace=namespace, limit=limit, filter=filter
                )
            except Exception as exc:
                span.record_exception(exc)
                raise
            span.set_attribute("result_count", len(results))
            return results

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        async with self._tracer.span("store.delete") as span:
            span.set_attribute("namespace", namespace)
            span.set_attribute("count", len(chunk_ids))
            try:
                await self._inner.delete(chunk_ids, namespace=namespace)
            except Exception as exc:
                span.record_exception(exc)
                raise

    async def delete_namespace(self, namespace: str) -> None:
        async with self._tracer.span("store.delete_namespace") as span:
            span.set_attribute("namespace", namespace)
            try:
                await self._inner.delete_namespace(namespace)
            except Exception as exc:
                span.record_exception(exc)
                raise

    def get_all_chunks(
        self,
        namespace: str,
        filter: dict[str, Any] | None = None,
    ) -> AsyncIterator[Chunk]:
        """Pass-through — async iterator; tracing happens at caller's discretion."""
        return self._inner.get_all_chunks(namespace=namespace, filter=filter)


__all__ = ["TracedEmbedder", "TracedReranker", "TracedRetriever", "TracedVectorStore"]
