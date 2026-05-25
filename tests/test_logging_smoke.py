# SPDX-License-Identifier: Apache-2.0
"""Smoke test that verifies key modules emit at least one log message during use."""

import hashlib
import logging

import pytest

from cenote.chunkers import RecursiveCharacterChunker
from cenote.embedders import CachedEmbedder, InMemoryCache, MockEmbedder
from cenote.models import Chunk, Document
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


@pytest.mark.asyncio
async def test_pipeline_emits_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="cenote")

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=0)
    chunks = chunker.chunk(Document(id="d", content="hello world"))

    embedder = CachedEmbedder(inner=MockEmbedder(dimensions=8), cache=InMemoryCache())
    embedded = await embedder.embed(chunks)

    store = InMemoryVectorStore(dimensions=8)
    await store.upsert(embedded, namespace="t")

    retriever = VectorRetriever(embedder=embedder, store=store)
    await retriever.retrieve("hello", namespace="t", limit=3)

    cenote_logs = [r for r in caplog.records if r.name.startswith("cenote.")]
    log_sources = {r.name for r in cenote_logs}
    assert len(cenote_logs) > 0, "expected at least one log from cenote.* modules"
    assert any("chunker" in s for s in log_sources), f"no chunker log, sources={log_sources}"
    assert any("embedders" in s for s in log_sources), f"no embedder log, sources={log_sources}"
    assert any("stores" in s for s in log_sources), f"no store log, sources={log_sources}"
    assert any("retrievers" in s for s in log_sources), f"no retriever log, sources={log_sources}"
