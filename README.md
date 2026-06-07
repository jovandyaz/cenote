# cenote

[![PyPI](https://img.shields.io/pypi/v/cenote-core)](https://pypi.org/project/cenote-core/)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/jovandyaz/cenote/badge)](https://scorecard.dev/viewer/?uri=github.com/jovandyaz/cenote)
[![CI](https://github.com/jovandyaz/cenote/actions/workflows/ci.yml/badge.svg)](https://github.com/jovandyaz/cenote/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jovandyaz/cenote/branch/main/graph/badge.svg)](https://codecov.io/gh/jovandyaz/cenote)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://jovandyaz.github.io/cenote/)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Production-grade RAG primitives for Python — Protocol-based, multi-tenant by design, type-strict from day one. Spanish-first since M1.1; the foundation for vertical agent products targeting LATAM regulated industries.

## Why cenote

cenote is **not** a LangChain alternative. LangChain is a kitchen-sink framework with ~100k stars and a full-time team. cenote is the opposite: a small, opinionated set of primitives for teams that hit framework complexity ceilings.

- **Production minimalist** — clear `Protocol` interfaces, composition over inheritance, engineering hardenings (batching, rate limiting, transactional upserts) built in.
- **Type-strict** — `mypy --strict` clean. `py.typed` shipped. Your IDE catches wiring errors before runtime.
- **Multi-tenant by design** — `namespace` is mandatory on every store and retriever method. Cross-tenant leakage is impossible by construction.
- **LATAM-first roadmap** — Spanish-aware BM25, ES evaluation datasets, fiscal/regulatory document support land in M1.1+. Multilingual embedders (Voyage, Cohere) already work today.

The name comes from cenotes — natural deep wells in the Yucatán Peninsula used by the Maya as sacred sources of fresh water and knowledge. The metaphor maps to RAG: a deep, structured source of knowledge from which you retrieve context.

## When NOT to use cenote

cenote is a focused library, not a universal RAG toolkit. Don't choose it when:

- **You need 100+ integrations out-of-the-box.** Use LangChain or LlamaIndex — they bundle adapters for nearly every vector DB, LLM, and embedder. cenote ships protocols and a few concrete impls; everything else is your code.
- **You want a hosted RAG service.** cenote is a library you install. For managed RAG, evaluate Vectara, Pinecone Assistants, or AWS Bedrock Knowledge Bases.
- **You need a chatbot UI out-of-the-box.** cenote doesn't ship UI. Pair it with `gradio`, `streamlit`, or your own web stack.
- **Your data is small (<10k chunks) and single-tenant.** A 50-line script with `numpy.dot` and SQLite is enough. cenote's multi-tenancy + production hardenings add value above that scale.
- **You can't adopt Python 3.12+.** cenote requires modern Python; we don't backport.

## Status

Shipped through **M1.2** — core primitives, Spanish-aware retrieval, observability, LLM client, and the `cenote.bench` harness. The current released version is the PyPI badge above; see [CHANGELOG.md](CHANGELOG.md) for the full history. Reflects actual code state, not roadmap intent.

| Module | Shipped | Roadmap |
|---|---|---|
| `cenote.models` | Document, Chunk, EmbeddedChunk, RetrievalResult, Message | — |
| `cenote.errors` | CenoteError hierarchy (Configuration, RateLimit, DimensionMismatch, Migration, LLM…) | — |
| `cenote.types` | Vector, Namespace, ModelId, ContentHash | — |
| `cenote.chunkers` | Chunker Protocol, RecursiveCharacterChunker, MarkdownChunker | Token-aware chunking |
| `cenote.embedders` | Embedder Protocol, MockEmbedder, VoyageEmbedder, CohereEmbedder, CachedEmbedder, EmbeddingCache Protocol, InMemoryCache, SqliteCache | RedisCache, streaming embed |
| `cenote.stores` | VectorStore Protocol, InMemoryVectorStore, PgVectorStore (HNSW + SET LOCAL transactional) | — |
| `cenote.retrievers` | Retriever Protocol, VectorRetriever, BM25Retriever (LRU-cached, picklable), HybridRetriever (RRF fusion) | — |
| `cenote.tokenizers` | Tokenizer Protocol, SpanishTokenizer (Snowball stemmer, pickle-safe since v0.4.1) | — |
| `cenote.rerankers` | Reranker Protocol, VoyageReranker, CohereReranker | — |
| `cenote.observability` | Tracer Protocol, NoopTracer, OTel adapter, Langfuse adapter, TracedVectorStore wrapper | — |
| `cenote.pipeline` | IndexingPipeline, IndexingProgress | Resume/retry-failed-batches API |
| `cenote.eval` | precision_at_k, recall_at_k, mean_reciprocal_rank, RetrievalBenchmark harness | DeepEval integration, bilingual EN/ES golden dataset |
| `cenote.bench` ([docs](docs/benchmarks.md)) | MiraclLoader, ranx-backed nDCG/Recall, RRF fusion, BenchRunner, Pyserini-2cr report, `cenote bench miracl-es` CLI | BEIR sanity check, MTEB-es retrieval slice, real MIRACL-es numbers (Phase F) |
| `cenote.llm` | LLMClient Protocol, AnthropicLLM (with prompt-cache awareness), NoopLLM | Tool use, `cenote-llm-{openai,bedrock,vertex}` as separate packages per [ADR-0008](docs/adrs/0008-monorepo-strategy.md) |
| `cenote.cli` | `cenote bench miracl-es` (Typer) | Additional subcommands as needs emerge |

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
- ✅ **M1.1** (released as v0.2.0) — MarkdownChunker, BM25 + Hybrid retrievers, Spanish-aware tokenizer, concrete rerankers, RetrievalBenchmark
- ✅ **M1.2** (released as v0.3.0) — OTel + Langfuse adapters, Traced wrappers, AnthropicLLM with prompt caching, SqliteCache
- ✅ **Foundation hardening** (v0.4.0) — Sigstore + SBOM + Trusted Publishing, release-please, gitlint, observability wrappers, hardening pass on retrievers (LRU cache + invalidation), HNSW SET LOCAL fix
- ✅ **Bug fixes** (v0.4.1) — SpanishTokenizer pickle-safe, `_http.retrying` honors Retry-After header, embedder `max_retries` raised to 6
- ✅ **Retrieval benchmark harness** (v0.5.0) — `cenote.bench` module with MIRACL-es loader, ranx-backed metrics, RRF fusion, Pyserini-2cr report generator, and `cenote bench miracl-es` CLI ([docs](docs/benchmarks.md), [ADR-0009](docs/adrs/0009-miracl-es-benchmark.md))
- ✅ **Maintenance + security** (v0.6.0–v0.6.1) — release-please changelog consolidation and tooling cleanup, `lxml>=6.1` security pin (CVE PYSEC-2026-87)
- 📋 **M1.3+** — Tool use in AnthropicLLM, RedisCache, agent primitives, CFDI domain pack, MIRACL-es Phase F (real numbers)

[See M1.1 baselines](docs/benchmarks/2026-05-27-m1-1-baselines.md) for the
Spanish BM25 + hybrid retrieval scaffold. Full Pyserini-2cr table follows after
the v0.5.0 Phase F embedding pass — see [docs/benchmarks.md](docs/benchmarks.md).

See [CHANGELOG.md](CHANGELOG.md) for a granular record of what shipped when.

## Downstream products

cenote is the shared core for a portfolio of vertical agents serving LATAM regulated industries. Each downstream product stays in its own repository (per [ADR-0008](docs/adrs/0008-monorepo-strategy.md)) and consumes cenote-core via PyPI.

**Committed** (Tier A):

- **cfdi-agent** — Accounting reconciliation + CFDI 4.0 compliance for Mexican PYMEs *(first vertical)*
- **kyc-agent** — KYC/AML for LATAM fintechs over CNBV, UIF, Banxico, DOF, PEP lists
- **bank-reco-agent** — Bank statement ↔ CFDI reconciliation (composes with cfdi-agent for higher ARPU)
- **knowtis-ai** — RAG + research agent over the Knowtis notes platform

**Validated post-Tier-A** (priority order based on internal analysis):

- **jurisprudencia-agent** — SCJN, Corte Constitucional CO, CSJN AR retrieval with audit-grade grounding
- **cofepris-agent** — Pharma regulatory intelligence over COFEPRIS, INVIMA, ANVISA, ANMAT
- **nomina-agent** (validate first) — LFT / IMSS / INFONAVIT copilot over existing payroll stacks

Each vertical validates cenote-core from a different angle: deterministic-correctness (cfdi, kyc, bank-reco), creative synthesis (knowtis-ai, jurisprudencia), regulatory tracking (cofepris).

## License

[Apache 2.0](LICENSE).

## Author

Jovan Díaz — [github.com/jovandyaz](https://github.com/jovandyaz)

Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md). Security: see [SECURITY.md](SECURITY.md).
