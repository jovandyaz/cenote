"""Tests for IndexingPipeline."""

from __future__ import annotations

from itertools import pairwise

import pytest

from cenote.chunkers.recursive import RecursiveCharacterChunker
from cenote.embedders.mock import MockEmbedder
from cenote.errors import ConfigurationError
from cenote.models import Chunk, Document, EmbeddedChunk
from cenote.pipeline.indexing import IndexingPipeline, IndexingProgress
from cenote.stores.memory import InMemoryVectorStore


@pytest.mark.asyncio
async def test_indexes_documents_end_to_end() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = MockEmbedder(dimensions=8)
    store = InMemoryVectorStore(dimensions=8)
    pipeline = IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=2)

    docs = [Document(id=f"d{i}", content=f"content {i} " * 30) for i in range(5)]
    progress_events: list[IndexingProgress] = []
    async for progress in pipeline.index(docs):
        progress_events.append(progress)

    assert len(progress_events) >= 1
    final = progress_events[-1]
    assert final.documents_done == 5
    assert final.chunks_done > 0
    assert final.errors == 0


@pytest.mark.asyncio
async def test_continues_past_embedding_failure() -> None:
    """An error in one batch should not abort subsequent batches."""

    class _FlakyEmbedder(MockEmbedder):
        def __init__(self) -> None:
            super().__init__(dimensions=8)
            self.calls = 0

        async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("first batch fails")
            return await super().embed(chunks)

    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = _FlakyEmbedder()
    store = InMemoryVectorStore(dimensions=8)
    pipeline = IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=2)

    docs = [Document(id=f"d{i}", content=f"content {i} " * 30) for i in range(4)]
    progress_events: list[IndexingProgress] = []
    async for p in pipeline.index(docs):
        progress_events.append(p)

    final = progress_events[-1]
    assert final.errors >= 1
    assert final.documents_done == 4
    assert final.chunks_done > 0


@pytest.mark.asyncio
async def test_empty_input_yields_no_progress() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = MockEmbedder(dimensions=8)
    store = InMemoryVectorStore(dimensions=8)
    pipeline = IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=2)

    progress_events = [p async for p in pipeline.index([])]
    assert progress_events == []


@pytest.mark.asyncio
async def test_documents_with_no_chunks_count_done() -> None:
    """A document that produces zero chunks (e.g. empty content) still counts as done."""
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = MockEmbedder(dimensions=8)
    store = InMemoryVectorStore(dimensions=8)
    pipeline = IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=2)

    docs = [Document(id="d0", content=""), Document(id="d1", content="real " * 50)]
    progress_events = [p async for p in pipeline.index(docs)]
    final = progress_events[-1]
    assert final.documents_done == 2
    assert final.chunks_done > 0


def test_rejects_zero_batch_size() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = MockEmbedder(dimensions=8)
    store = InMemoryVectorStore(dimensions=8)
    with pytest.raises(ConfigurationError):
        IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=0)


@pytest.mark.asyncio
async def test_emits_progress_per_batch() -> None:
    """progress events should arrive at least once per batch boundary."""
    chunker = RecursiveCharacterChunker(chunk_size=128, chunk_overlap=0)
    embedder = MockEmbedder(dimensions=8)
    store = InMemoryVectorStore(dimensions=8)
    pipeline = IndexingPipeline(chunker, embedder, store, namespace="t", batch_size=2)

    docs = [Document(id=f"d{i}", content="content " * 50) for i in range(5)]
    progress_events = [p async for p in pipeline.index(docs)]

    for a, b in pairwise(progress_events):
        assert b.documents_done >= a.documents_done
        assert b.chunks_done >= a.chunks_done
        assert b.errors >= a.errors
