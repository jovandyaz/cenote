# SPDX-License-Identifier: Apache-2.0
"""End-to-end demo proving Phase 4 + Phase 5 deliverables work in practice."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from cenote.chunkers import RecursiveCharacterChunker
from cenote.embedders import MockEmbedder
from cenote.models import Chunk, Document, EmbeddedChunk, RetrievalResult
from cenote.observability import SpanContext
from cenote.observability.wrappers import TracedVectorStore
from cenote.pipeline import IndexingPipeline, IndexingProgress
from cenote.retrievers import BM25Retriever, HybridRetriever
from cenote.stores import InMemoryVectorStore
from cenote.tokenizers import SpanishTokenizer


def _header(title: str) -> None:
    print(f"\n=== {title}")


async def scenario_1_indexing_pipeline() -> InMemoryVectorStore:
    _header("Scenario 1 — Phase 4.8 IndexingPipeline")
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    store = InMemoryVectorStore(dimensions=64)
    pipeline = IndexingPipeline(
        chunker, MockEmbedder(dimensions=64), store, namespace="demo", batch_size=3
    )
    docs = [
        Document(id=f"doc-{i}", content=f"Documento {i} sobre cenotes en Yucatán. " * 10)
        for i in range(7)
    ]
    events: list[IndexingProgress] = [p async for p in pipeline.index(docs)]
    final = events[-1]
    assert final.documents_done == 7, f"expected 7 docs, got {final.documents_done}"
    assert final.errors == 0, f"expected 0 errors, got {final.errors}"
    print(f"[OK] indexed {final.chunks_done} chunks across {len(events)} progress events")
    return store


async def scenario_2_hybrid_resilience() -> None:
    _header("Scenario 2 — Phase 4.5 HybridRetriever resilience")

    class _FailingRetriever:
        async def retrieve(
            self, query: str, namespace: str, limit: int = 10, filter: Any = None
        ) -> list[RetrievalResult]:
            raise RuntimeError("simulated downstream failure")

    class _HealthyRetriever:
        async def retrieve(
            self, query: str, namespace: str, limit: int = 10, filter: Any = None
        ) -> list[RetrievalResult]:
            chunk = Chunk(
                id="healthy:0",
                document_id="healthy",
                content="cenote es un pozo natural",
                position=0,
                content_hash="deadbeef",
            )
            return [RetrievalResult(chunk=chunk, score=0.9, retriever="healthy")]

    hybrid = HybridRetriever(retrievers=[_FailingRetriever(), _HealthyRetriever()])
    results = await hybrid.retrieve("cenote", namespace="demo", limit=5)
    assert len(results) == 1, f"expected 1 fused result, got {len(results)}"
    assert "cenote" in results[0].chunk.content
    print("[OK] failing retriever tolerated; healthy result fused into output")


async def scenario_3_bm25_lru_eviction() -> None:
    _header("Scenario 3 — Phase 4.6 BM25Retriever LRU eviction")
    store = InMemoryVectorStore(dimensions=4)
    for ns in ("a", "b", "c"):
        chunk = Chunk(id=f"{ns}:0", document_id=ns, content="cenote", position=0, content_hash=ns)
        ec = EmbeddedChunk(
            chunk=chunk, embedding=[0.1, 0.2, 0.3, 0.4], embedding_model="mock:demo", dimensions=4
        )
        await store.upsert([ec], namespace=ns)
    retriever = BM25Retriever(store=store, tokenizer=SpanishTokenizer(), max_cached_namespaces=2)
    await retriever.retrieve("cenote", namespace="a", limit=1)
    await retriever.retrieve("cenote", namespace="b", limit=1)
    print(f"after a,b -> cache keys: {list(retriever._caches.keys())}")
    await retriever.retrieve("cenote", namespace="c", limit=1)
    print(f"after c   -> cache keys: {list(retriever._caches.keys())}")
    assert "a" not in retriever._caches, "expected 'a' to be evicted"
    assert set(retriever._caches.keys()) == {"b", "c"}
    print("[OK] LRU evicted 'a' once 'c' pushed the cache past max=2")


async def scenario_4_traced_store(store: InMemoryVectorStore) -> None:
    _header("Scenario 4 — Phase 4.7 TracedVectorStore")
    spans: list[tuple[str, dict[str, Any]]] = []

    class _RecordingSpan:
        def __init__(self, attrs: dict[str, Any]) -> None:
            self._attrs = attrs

        def set_attribute(self, key: str, value: Any) -> None:
            self._attrs[key] = value

        def record_exception(self, exception: BaseException) -> None:
            self._attrs["exception"] = repr(exception)

    class _RecordingTracer:
        @asynccontextmanager
        async def span(
            self, name: str, attributes: dict[str, Any] | None = None
        ) -> AsyncIterator[SpanContext]:
            attrs: dict[str, Any] = dict(attributes or {})
            spans.append((name, attrs))
            yield _RecordingSpan(attrs)

    await TracedVectorStore(store, _RecordingTracer()).search([0.1] * 64, namespace="demo", limit=3)
    names = [n for n, _ in spans]
    assert "store.search" in names, f"expected 'store.search' span, got {names}"
    search_attrs = next(a for n, a in spans if n == "store.search")
    print(f"[OK] emitted spans: {names}; store.search attrs: {search_attrs}")


def scenario_5_gitlint_smoke() -> None:
    _header("Scenario 5 — Phase 5 gitlint commit-msg smoke test")
    fixtures: list[tuple[str, int]] = [
        ("chore(verify): test scoped", 0),
        ("feat: add foo", 0),
        ("BAD MESSAGE NO PREFIX", 1),
        ("release: 0.4.0", 1),
    ]
    for msg, expected in fixtures:
        proc = subprocess.run(
            ["uv", "run", "gitlint"],  # noqa: S607 — `uv` resolved from PATH by design
            input=msg,
            text=True,
            capture_output=True,
            check=False,
        )
        verdict = "OK" if proc.returncode == expected else "FAIL"
        print(f"[{verdict}] {msg!r} -> exit={proc.returncode} (expected {expected})")
        assert proc.returncode == expected, (
            f"gitlint mismatch for {msg!r}: got {proc.returncode}, expected {expected}"
        )


async def main() -> None:
    store = await scenario_1_indexing_pipeline()
    await scenario_2_hybrid_resilience()
    await scenario_3_bm25_lru_eviction()
    await scenario_4_traced_store(store)
    scenario_5_gitlint_smoke()
    print("\nALL DEMOS PASSED")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
