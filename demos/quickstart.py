"""End-to-end demo: index a small corpus, retrieve, print results.

Usage:
    # With MockEmbedder (no API key, deterministic, dev mode):
    uv run python demos/quickstart.py --provider mock

    # With Voyage AI (requires VOYAGE_API_KEY):
    uv run python demos/quickstart.py --provider voyage

    # With Cohere multilingual (requires COHERE_API_KEY):
    uv run python demos/quickstart.py --provider cohere
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from cenote.chunkers import RecursiveCharacterChunker
from cenote.embedders import (
    CachedEmbedder,
    CohereEmbedder,
    Embedder,
    InMemoryCache,
    MockEmbedder,
    VoyageEmbedder,
)
from cenote.models import Document
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore

DATA_FILE = Path(__file__).parent / "data" / "wikipedia_snippets.json"

SAMPLE_QUERIES = [
    "What is a cenote?",
    "How does hybrid retrieval combine results?",
    "Tell me about vector databases.",
    "What does RRF stand for?",
]


def build_embedder(provider: str) -> Embedder:
    if provider == "mock":
        return MockEmbedder(dimensions=128)
    if provider == "voyage":
        key = os.environ["VOYAGE_API_KEY"]
        return VoyageEmbedder(api_key=key, model="voyage-3", dimensions=1024)
    if provider == "cohere":
        key = os.environ["COHERE_API_KEY"]
        return CohereEmbedder(api_key=key, model="embed-multilingual-v3.0", dimensions=1024)
    raise ValueError(f"unknown provider: {provider}")


async def run(provider: str, limit: int) -> None:
    data = json.loads(DATA_FILE.read_text())
    docs = [
        Document(id=d["id"], content=d["content"], metadata={"title": d["title"]}) for d in data
    ]

    chunker = RecursiveCharacterChunker(chunk_size=512, chunk_overlap=64)
    chunks = [c for doc in docs for c in chunker.chunk(doc)]

    embedder: Embedder = CachedEmbedder(inner=build_embedder(provider), cache=InMemoryCache())
    embedded = await embedder.embed(chunks)

    store = InMemoryVectorStore(dimensions=embedder.dimensions)
    await store.upsert(embedded, namespace="demo")
    retriever = VectorRetriever(embedder=embedder, store=store)

    for query in SAMPLE_QUERIES:
        print(f"\n=== Query: {query}")
        results = await retriever.retrieve(query, namespace="demo", limit=limit)
        for i, r in enumerate(results, 1):
            title = r.chunk.metadata.get("title", "?")
            snippet = r.chunk.content[:120].replace("\n", " ")
            print(f"  {i}. [score={r.score:.3f}] ({title}) {snippet}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="cenote quickstart demo")
    parser.add_argument("--provider", choices=["mock", "voyage", "cohere"], default="mock")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(run(args.provider, args.limit))


if __name__ == "__main__":
    main()
