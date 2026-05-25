# SPDX-License-Identifier: Apache-2.0
"""Example: implement the Embedder protocol from scratch.

Demonstrates structural typing — no inheritance from any cenote class.
The `HashEmbedder` below is recognized as an `Embedder` because it has
the right method/property shapes, period.

Run:
    uv run python examples/custom_embedder.py
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import random

from cenote.embedders import CachedEmbedder, InMemoryCache
from cenote.models import Chunk, Document, EmbeddedChunk
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore


class HashEmbedder:
    """Deterministic unit-norm embedder that derives vectors from text hashes.

    Useful when you need an embedder that:
        - has no API key
        - returns reproducible results across processes
        - shows the same distributional properties (unit-norm) as real embedders
    """

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    @property
    def model_id(self) -> str:
        return f"hash:{self._dimensions}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=c,
                embedding=self._vec(c.content),
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for c in chunks
        ]

    async def embed_query(self, query: str) -> list[float]:
        return self._vec(query)

    def _vec(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")
        rng = random.Random(seed)
        raw = [rng.gauss(0.0, 1.0) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]


async def main() -> None:
    # The HashEmbedder is recognized as an Embedder by cenote — no inheritance.
    raw_embedder = HashEmbedder(dimensions=128)
    embedder = CachedEmbedder(inner=raw_embedder, cache=InMemoryCache())

    store = InMemoryVectorStore(dimensions=128)
    retriever = VectorRetriever(embedder=embedder, store=store)

    docs = [
        Document(id="d1", content="Cenotes are natural sinkholes in the Yucatán Peninsula."),
        Document(id="d2", content="Vector databases index high-dimensional vectors."),
        Document(id="d3", content="Reciprocal Rank Fusion combines multiple ranked lists."),
    ]
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.append(
            Chunk(
                id=Chunk.make_id(doc.id, 0),
                document_id=doc.id,
                content=doc.content,
                position=0,
                content_hash=hashlib.sha256(doc.content.encode()).hexdigest(),
            )
        )

    embedded = await embedder.embed(chunks)
    await store.upsert(embedded, namespace="custom-embedder-demo")

    print("Custom embedder model_id:", embedder.model_id)
    print(f"Indexed {len(embedded)} chunks. Running 2 queries:\n")
    for query in ["What is a cenote?", "How does RRF work?"]:
        results = await retriever.retrieve(query, namespace="custom-embedder-demo", limit=2)
        print(f"Query: {query}")
        for r in results:
            print(f"  [{r.score:+.3f}] {r.chunk.content}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
