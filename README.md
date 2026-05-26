# cenote

[![CI](https://github.com/jovandyaz/cenote/actions/workflows/ci.yml/badge.svg)](https://github.com/jovandyaz/cenote/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jovandyaz/cenote/branch/main/graph/badge.svg)](https://codecov.io/gh/jovandyaz/cenote)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://jovandyaz.github.io/cenote/)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Production-grade RAG primitives for Python — Protocol-based, multi-tenant by design, type-strict from day one. Targeting Spanish/LATAM workloads from M1.1.

## Why cenote

cenote is **not** a LangChain alternative. LangChain is a kitchen-sink framework with ~100k stars and a full-time team. cenote is the opposite: a small, opinionated set of primitives for teams that hit framework complexity ceilings.

- **Production minimalist** — clear `Protocol` interfaces, composition over inheritance, engineering hardenings (batching, rate limiting, transactional upserts) built in.
- **Type-strict** — `mypy --strict` clean. `py.typed` shipped. Your IDE catches wiring errors before runtime.
- **Multi-tenant by design** — `namespace` is mandatory on every store and retriever method. Cross-tenant leakage is impossible by construction.
- **LATAM-first roadmap** — Spanish-aware BM25, ES evaluation datasets, fiscal/regulatory document support land in M1.1+. Multilingual embedders (Voyage, Cohere) already work today.

The name comes from cenotes — natural deep wells in the Yucatán Peninsula used by the Maya as sacred sources of fresh water and knowledge. The metaphor maps to RAG: a deep, structured source of knowledge from which you retrieve context.

## Status

| Module | M1.0 (released) | M1.1+ (planned) |
|---|---|---|
| `cenote.models` | ✓ Document, Chunk, EmbeddedChunk, RetrievalResult | — |
| `cenote.errors` | ✓ CenoteError hierarchy | — |
| `cenote.types` | ✓ Vector, Namespace, ModelId, ContentHash | — |
| `cenote.chunkers` | ✓ Chunker Protocol, RecursiveCharacterChunker | MarkdownChunker, token-aware chunking |
| `cenote.embedders` | ✓ Embedder Protocol, MockEmbedder, VoyageEmbedder, CohereEmbedder, EmbeddingCache, InMemoryCache, CachedEmbedder | Streaming embed, SqliteCache, RedisCache |
| `cenote.stores` | ✓ VectorStore Protocol, InMemoryVectorStore, PgVectorStore | — |
| `cenote.retrievers` | ✓ Retriever Protocol, VectorRetriever | BM25Retriever, HybridRetriever (RRF), Spanish-aware tokenizer |
| `cenote.rerankers` | ✓ Reranker Protocol (no impl) | VoyageReranker, CohereReranker |
| `cenote.observability` | ✓ Tracer Protocol, NoopTracer | OTel adapter, Langfuse adapter |
| `cenote.eval` | ✓ precision_at_k, recall_at_k, mean_reciprocal_rank | DeepEval integration, bilingual EN/ES dataset |
| `cenote.llm` | — | Anthropic Claude wrapper with prompt-cache awareness |

## Quickstart

```bash
pip install cenote-core
```

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

    doc = Document(id="d1", content="Cenotes are natural sinkholes in the Yucatán Peninsula.")
    chunks = chunker.chunk(doc)
    embedded = await embedder.embed(chunks)
    await store.upsert(embedded, namespace="quickstart")

    results = await retriever.retrieve("What is a cenote?", namespace="quickstart", limit=3)
    for r in results:
        print(f"[{r.score:.3f}] {r.chunk.content}")


asyncio.run(main())
```

For real semantic retrieval, swap `MockEmbedder` for `VoyageEmbedder(api_key=..., model="voyage-3")` or `CohereEmbedder(api_key=..., model="embed-multilingual-v3.0")`. For production storage, `PgVectorStore.connect(dsn, dimensions=...)`.

→ Full quickstart: <https://jovandyaz.github.io/cenote/quickstart/>

## Extending cenote

Every primitive is a `typing.Protocol` — implement the interface and plug it in. No inheritance required.

```python
from cenote.models import Chunk, EmbeddedChunk
from cenote.types import Vector


class MyEmbedder:
    """Satisfies the Embedder protocol via structural typing."""

    @property
    def model_id(self) -> str:
        return "my-provider:my-model"

    @property
    def dimensions(self) -> int:
        return 768

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        ...

    async def embed_query(self, query: str) -> Vector:
        ...
```

→ Full example: [examples/custom_embedder.py](examples/custom_embedder.py)
→ Custom chunker: <https://jovandyaz.github.io/cenote/extending/custom-chunker/>

## Architecture

Three diagrams document the system at different zoom levels:

- [**Ecosystem**](docs/diagrams/01-ecosystem.drawio) — cenote's position in the wider RAG ecosystem
- [**Internal architecture**](docs/diagrams/02-architecture.drawio) — 5 layers + future-API stubs
- [**Runtime flow**](docs/diagrams/03-runtime-flow.drawio) — indexing path and query path sequence

GitHub renders `.drawio` files inline natively (since 2024). Click any link above to view.

→ Full architecture page: <https://jovandyaz.github.io/cenote/architecture/>

## Roadmap

- ✅ **M1.0** (released as v0.1.0) — Core primitives: chunker, embedders, stores, retrievers, future-API stubs
- 🚧 **M1.1** — MarkdownChunker, BM25 + Hybrid retrievers, Spanish-aware tokenizer, concrete rerankers, DeepEval integration
- 📋 **M1.2+** — OTel/Langfuse adapters, LLM client (Anthropic Claude with prompt caching), agent primitives, CFDI domain pack

See [CHANGELOG.md](CHANGELOG.md) for a granular record of what shipped when.

## Downstream products

cenote is the shared core for two products in development:

- **knowtis-ai** — RAG + research agent over the Knowtis notes platform
- **cfdi-agent** — Accounting reconciliation + CFDI 4.0 compliance for Mexican PYMEs

Each downstream product validates cenote from opposite ends: knowtis-ai favors creative synthesis, cfdi-agent demands deterministic correctness with audit trails.

## License

[Apache 2.0](LICENSE).

## Author

Jovan Díaz — [github.com/jovandyaz](https://github.com/jovandyaz)

Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md). Security: see [SECURITY.md](SECURITY.md).
