# Quickstart

This guide takes you from `pip install cenote-core` to a working semantic search in under 5 minutes.

## Install

```bash
pip install cenote-core
# or
uv add cenote-core
```

## Index and retrieve

```python
import asyncio
from cenote.chunkers import RecursiveCharacterChunker
from cenote.embedders import MockEmbedder
from cenote.models import Document
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore


async def main() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=512, chunk_overlap=64)
    embedder = MockEmbedder(dimensions=128)
    store = InMemoryVectorStore(dimensions=128)
    retriever = VectorRetriever(embedder=embedder, store=store)

    docs = [
        Document(id="d1", content="Cenotes are natural sinkholes in the Yucatán Peninsula."),
        Document(id="d2", content="Vector databases index high-dimensional vectors."),
        Document(id="d3", content="RRF combines results from multiple ranked lists."),
    ]
    chunks = [c for d in docs for c in chunker.chunk(d)]
    embedded = await embedder.embed(chunks)
    await store.upsert(embedded, namespace="quickstart")

    results = await retriever.retrieve("What is a cenote?", namespace="quickstart", limit=2)
    for r in results:
        print(f"[{r.score:.3f}] {r.chunk.content}")


asyncio.run(main())
```

## Use real embedders

`MockEmbedder` produces deterministic vectors and is useful for testing. For real semantic retrieval, swap in `VoyageEmbedder` or `CohereEmbedder`:

```python
import os
from cenote.embedders import VoyageEmbedder

embedder = VoyageEmbedder(
    api_key=os.environ["VOYAGE_API_KEY"],
    model="voyage-3",
    dimensions=1024,
)
```

Both `VoyageEmbedder` and `CohereEmbedder` support multilingual content, automatic batching, and optional RPM rate limiting.

## Use Postgres for production storage

`InMemoryVectorStore` is great for tests and small corpora. For production scale, use `PgVectorStore`:

```python
from cenote.stores import PgVectorStore

store = await PgVectorStore.connect(
    "postgresql://user:pass@localhost:5432/cenote",
    dimensions=1024,
)
await store.apply_migrations()
```

See [examples/pgvector_setup.py](https://github.com/jovandyaz/cenote/blob/main/examples/pgvector_setup.py) for a complete production setup.

## Next steps

- [API Reference](api/models.md)
- [Extending cenote — custom embedders](extending/custom-embedder.md)
- [Architecture](architecture.md)
