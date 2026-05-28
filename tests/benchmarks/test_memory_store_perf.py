# SPDX-License-Identifier: Apache-2.0
"""Performance benchmark for InMemoryVectorStore cosine search over 10k vectors."""

from __future__ import annotations

import asyncio

import pytest

from cenote.models import Chunk, EmbeddedChunk
from cenote.stores.memory import InMemoryVectorStore


@pytest.mark.benchmark
def test_memory_store_search_10k_vectors_1024d(benchmark) -> None:
    """Cosine search top-10 over 10k vectors of dim 1024."""
    store = InMemoryVectorStore(dimensions=1024)
    chunks = [
        EmbeddedChunk(
            chunk=Chunk(
                id=f"c{i}",
                document_id=f"d{i}",
                content=f"text {i}",
                position=0,
                content_hash=f"h{i}",
            ),
            embedding=[(i + j) * 0.001 for j in range(1024)],
            embedding_model="mock:default",
            dimensions=1024,
        )
        for i in range(10000)
    ]
    asyncio.run(store.upsert(chunks, namespace="bench"))
    query = [0.5] * 1024

    def _search() -> None:
        asyncio.run(store.search(query, namespace="bench", limit=10))

    benchmark(_search)
