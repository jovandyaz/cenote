# SPDX-License-Identifier: Apache-2.0
"""Example: production setup with PgVectorStore.

Demonstrates:
    - Connect with startup retry (tolerates container-not-ready races)
    - Apply migrations idempotently
    - Upsert a small corpus
    - Query with namespace isolation
    - Cleanup

Prerequisites:
    - Postgres with pgvector extension running
    - For local testing: docker compose -f docker-compose.test.yml up -d
    - TEST_DATABASE_URL env var (defaults to the local docker-compose URL)

Run:
    docker compose -f docker-compose.test.yml up -d
    uv run python examples/pgvector_setup.py
    docker compose -f docker-compose.test.yml down -v
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid

from cenote.embedders import MockEmbedder
from cenote.models import Chunk
from cenote.retrievers import VectorRetriever
from cenote.stores import PgVectorStore

DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://cenote:cenote@localhost:5433/cenote_test",
)
DIMENSIONS = 64


def _chunk(text: str, idx: int, doc_id: str = "doc") -> Chunk:
    return Chunk(
        id=Chunk.make_id(doc_id, idx),
        document_id=doc_id,
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


async def main() -> None:
    print(f"Connecting to {DSN}...")
    store = await PgVectorStore.connect(DSN, dimensions=DIMENSIONS, startup_retries=10)
    print("Applying migrations...")
    await store.apply_migrations()

    embedder = MockEmbedder(dimensions=DIMENSIONS)
    retriever = VectorRetriever(embedder=embedder, store=store)

    tenant_a = f"tenant-a-{uuid.uuid4()}"
    tenant_b = f"tenant-b-{uuid.uuid4()}"

    corpus_a = ["cenotes are sacred wells", "pyramids in the yucatán"]
    corpus_b = ["pgvector adds vector search", "postgres is a relational database"]

    chunks_a = [_chunk(t, i, doc_id="doc-a") for i, t in enumerate(corpus_a)]
    chunks_b = [_chunk(t, i, doc_id="doc-b") for i, t in enumerate(corpus_b)]

    print(f"Indexing {len(chunks_a)} chunks into namespace {tenant_a}")
    embedded_a = await embedder.embed(chunks_a)
    await store.upsert(embedded_a, namespace=tenant_a)

    print(f"Indexing {len(chunks_b)} chunks into namespace {tenant_b}")
    embedded_b = await embedder.embed(chunks_b)
    await store.upsert(embedded_b, namespace=tenant_b)

    print(f"\nQuerying tenant_a={tenant_a} for 'sacred wells'...")
    results = await retriever.retrieve("sacred wells", namespace=tenant_a, limit=2)
    for r in results:
        print(f"  [{r.score:+.3f}] {r.chunk.content}")

    print(f"\nQuerying tenant_b={tenant_b} for 'vector search'...")
    results = await retriever.retrieve("vector search", namespace=tenant_b, limit=2)
    for r in results:
        print(f"  [{r.score:+.3f}] {r.chunk.content}")

    print("\nVerifying namespace isolation: querying tenant_a with tenant_b's vocabulary...")
    results = await retriever.retrieve("pgvector", namespace=tenant_a, limit=5)
    contents = {r.chunk.content for r in results}
    assert "pgvector adds vector search" not in contents, (
        "namespace isolation FAILED — tenant_b leaked into tenant_a"
    )
    print("  Isolation verified: tenant_b's chunks are not visible from tenant_a.")

    print("\nCleanup: dropping both namespaces.")
    await store.delete_namespace(tenant_a)
    await store.delete_namespace(tenant_b)
    await store.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
