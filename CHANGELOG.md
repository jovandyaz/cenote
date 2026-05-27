# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 disclaimer.** APIs may break in any minor release until `1.0.0` ships.
> Patch releases (`0.1.0` → `0.1.1`) are bug fixes only.

## [Unreleased]

### Added

- `VectorStore.get_all_chunks(namespace, filter)` async iterator added to the
  Protocol. `InMemoryVectorStore` impl trivially iterates the namespace dict;
  `PgVectorStore` impl uses an asyncpg server-side cursor with `prefetch=200`
  for memory-bounded iteration over large namespaces. Migration `003` is a
  no-op placeholder (the `(namespace, id)` PK from `002` already provides the
  needed index). Drives BM25Retriever index builds in subsequent tasks.
- `cenote.tokenizers` subpackage: `Tokenizer` Protocol +
  `SpanishTokenizer` (Snowball-ES stemming via `PyStemmer`, ~440-word
  inline `SPANISH_STOPWORDS` frozenset, NFD accent fold). Drives
  Spanish-aware BM25 retrieval in M1.1.
- `cenote.chunkers.MarkdownChunker`: structure-aware splitter respecting
  heading boundaries (H1-H3 by default), fenced code blocks, tables,
  blockquotes, and lists as atomic units. Long sections fall back to
  `RecursiveCharacterChunker` while heading hierarchy is preserved in
  `chunk.metadata['headings']` and prepended to `chunk.content` per the
  Chunker contract.
- `cenote.retrievers.BM25Retriever`: Okapi BM25 over chunks lazily loaded
  from any `VectorStore` via `get_all_chunks`. Per-namespace index cached for
  the retriever lifetime; `from_chunks(chunks, tokenizer)` builds without a
  store. Metadata filters supported. Runtime dep: `rank_bm25>=0.2.2`.
- `cenote.rerankers.VoyageReranker`: production-grade cross-encoder reranker
  over Voyage's `/v1/rerank`. Batching (≤1000/req), concurrency caps,
  exponential-backoff retries on 429/5xx, optional RPM rate limiting —
  mirrors `VoyageEmbedder` hardenings. `retriever` is normalized to
  `<original>+rerank:voyage` on every result.
- `cenote.rerankers.CohereReranker`: production-grade multilingual reranker
  over Cohere's `/v2/rerank` (default model `rerank-3.5-multilingual`). Same
  hardenings pattern as `VoyageReranker`; `retriever` normalized to
  `<original>+rerank:cohere`.
- `cenote.rerankers._http_reranker._HTTPReranker`: shared base class capturing
  Voyage/Cohere common HTTP rerank machinery (batching, semaphore, retries,
  rate limiting). Provider impls now declare ~10 lines of constants +
  `_payload`. Adding a new provider costs ~15 lines. Also defends against
  invalid/duplicate indices in provider responses with a logged skip.
- Test factories consolidated to `tests/_factories.py` (`make_chunk`,
  `make_embedded`, `make_result`). Replaces 5 near-duplicate helpers across
  store/retriever/reranker test files.

## [0.1.0] - 2026-05-25

### Added

- PyPI package name: `cenote-core` (aligns with `langchain-core`,
  `llama-index-core`, `pydantic-core` ecosystem patterns). Import remains
  `import cenote` (Pillow/scikit-learn precedent — distribution name and
  import name need not match).
- GitHub repo renamed `pycenote` → `cenote` (brand umbrella; GitHub
  auto-redirects old URLs).
- `CONTRIBUTING.md` with dev setup, test commands, code style, commit
  conventions, and the release process via PyPI Trusted Publishing.
- Full README rewrite with new positioning ("not a LangChain alternative —
  production minimalist for teams that hit framework complexity ceilings"),
  module status table split into M1.0 / M1.1+ columns, expanded quickstart,
  extension example with structural-typing pattern, architecture section
  with diagram links, and roadmap with realistic M1.0/M1.1/M1.2+ scope.
- GitHub Actions release workflow with PyPI OIDC trusted publishing.
  Triggers on `v*` tag push and publishes to <https://pypi.org/project/cenote-core/>.
  Requires one-time setup on PyPI to register the pending publisher.
- Cookbook: `examples/custom_embedder.py` (structural-typing demo — implement
  the `Embedder` protocol without inheritance) and `examples/pgvector_setup.py`
  (production PgVectorStore — connect with retry, apply migrations,
  multi-tenant indexing, namespace isolation verification).
- `examples` added to ruff src list.
- Documentation site powered by `mkdocs-material` and `mkdocstrings-python`.
  Deployed to GitHub Pages at <https://jovandyaz.github.io/cenote/> via
  GitHub Actions on every push to main. Includes auto-generated API
  reference, quickstart, architecture page linking to drawio diagrams, and
  extension tutorials for custom embedders and chunkers.
- `mkdocs-material`, `mkdocstrings-python` added as dev dependencies.
- Docs badge added to README. Diagrams link directly to GitHub's native
  drawio renderer (no PNG exports needed).
- PgVectorStore unit-level test coverage raised from 21% to ≥80% via
  `tests/stores/test_pgvector_helpers.py` (pure helpers, no Postgres
  dependency). Integration tests continue to cover the database layer.
- Codecov integration: CI uploads `coverage.xml` to Codecov on every push
  to main; coverage badge added to README. Requires `CODECOV_TOKEN` secret.
- Structured logging via `logging.getLogger(__name__)` in every non-trivial
  module under `src/cenote/`. Key events emit at DEBUG; transient failures
  (retries, rate-limit waits) emit at WARNING. No `print()` calls remain.
- `cenote.types` module with public type aliases (`Vector`, `Namespace`,
  `ModelId`, `ContentHash`). Adopted in public signatures of `Embedder`,
  `EmbeddingCache`, `VectorStore`.
- `cenote.errors` exception hierarchy: `CenoteError`, `ConfigurationError`,
  `EmbeddingError`, `RateLimitError`, `VectorStoreError`, `DimensionMismatchError`,
  `MigrationError`. Replaces bare `ValueError` raises throughout `src/cenote/`.
- `cenote.models`: `Document`, `Chunk`, `EmbeddedChunk`, `RetrievalResult`
  Pydantic v2 models with `extra="forbid"`. `Chunk.make_id(doc_id, pos)`
  produces deterministic chunk IDs.
- `cenote.chunkers`: `Chunker` Protocol (with `chunk.content` contract docstring)
  and `RecursiveCharacterChunker` (priority-list separators, configurable
  `chunk_size=512` and `chunk_overlap=50`, deep-copied metadata, unicode-safe).
- `cenote.embedders`: `Embedder` Protocol (`model_id`, `dimensions`, async
  `embed`/`embed_query`) and `MockEmbedder` (deterministic unit-norm vectors
  derived from content hash; matches real-embedder distribution to surface
  ranking bugs that raw Gaussian vectors would hide).
- `cenote.embedders.cache`: `EmbeddingCache` Protocol, `InMemoryCache`
  (dict-backed, copies on `set` to avoid poisoning), and `CachedEmbedder`
  wrapper (slot-array preserves input order; only cache misses hit the
  inner embedder; cache key is `(model_id, content_hash)` so different
  models do not collide).
- `cenote.embedders.voyage.VoyageEmbedder` and
  `cenote.embedders.cohere.CohereEmbedder`: production-grade multilingual
  embedders over Voyage AI and Cohere v2 REST APIs. Both ship with input
  batching (Voyage ≤128/req, Cohere ≤96/req), concurrency caps via
  `asyncio.Semaphore`, exponential-backoff retries on 429/5xx, and an
  optional sliding-window RPM rate limiter.
- `cenote.embedders._http`: shared `RateLimiter` (sliding window, lock-coordinated
  across tasks) and `retrying(...)` helper.
- Runtime dep: `httpx>=0.27`. Dev dep: `respx>=0.21` (HTTP mocking — no real
  API calls in CI).
- `.env.example`: template for `VOYAGE_API_KEY`, `COHERE_API_KEY`.
- `cenote.stores`: `VectorStore` Protocol (multi-tenant, `namespace` mandatory
  on every method) and `InMemoryVectorStore` (numpy-backed cosine similarity,
  per-namespace dicts, optional metadata-filter via exact JSONB-style match).
  Production-grade backend (PgVectorStore) lands in a later task.
- Runtime dep: `numpy>=2.0`.
- `cenote.retrievers`: `Retriever` Protocol and `VectorRetriever` (composes
  any `Embedder` with any `VectorStore`; embeds the query, searches the store,
  normalizes `retriever="vector"` on every `RetrievalResult`).
- `cenote.stores.PgVectorStore`: production-grade `VectorStore` backed by
  Postgres + pgvector. Hardenings: transactional `upsert`/`delete`,
  idempotent migrations tracking (`cenote_schema_migrations` table),
  exponential-backoff `connect()` retry on container-not-ready races,
  pre-flight dimension validation, configurable HNSW `m` /
  `ef_construction` (migration template) and runtime `ef_search`. Initial
  schema in `001_init.sql` ships a GIN index on `metadata` so `@>` filters
  are O(log n) instead of seq-scan.
- `docker-compose.test.yml`: `pgvector/pgvector:pg16` container on port 5433
  for local integration tests.
- CI: new `integration-tests` job spins up a Postgres service container,
  exports `TEST_DATABASE_URL`, and runs `pytest -m integration`.
- Runtime dep: `asyncpg>=0.30`. Dev dep: `asyncpg-stubs>=0.31.2` (types).
- `demos/quickstart.py`: end-to-end demo CLI — indexes a small EN corpus
  (`demos/data/wikipedia_snippets.json`, 20 entries) through chunker +
  embedder + in-memory store, then runs sample queries against
  `VectorRetriever`. `--provider {mock,voyage,cohere}` toggles between the
  no-API mock and the real multilingual embedders. Smoke test
  (`tests/demos/test_quickstart_smoke.py`) runs the mock path on every CI.
- README: added `## Quickstart` section with the three provider invocations
  and softened the "LATAM-rooted" claim to match what M1.0 actually ships
  (multilingual embedders today; Spanish-specific BM25 + ES eval datasets
  on the M1.1+ roadmap).
- `cenote.rerankers.Reranker` Protocol (no impl yet — concrete
  `VoyageReranker` / `CohereReranker` ship in M1.1).
- `cenote.observability`: `Tracer` Protocol + `NoopTracer` default. OTel and
  Langfuse adapters land in M1.1 without breaking the API.
- `cenote.eval.metrics`: BEIR-style retrieval quality helpers —
  `precision_at_k`, `recall_at_k`, `mean_reciprocal_rank`. DeepEval
  integration arrives in M1.1.
- Initial project scaffolding: `uv`, `ruff`, `mypy --strict`, `pytest`, `pre-commit`,
  GitHub Actions CI (lint + type + unit tests, Python 3.12 & 3.13, `pip-audit`).
- `LICENSE` (Apache 2.0), `CHANGELOG.md`, `SECURITY.md`.
- `py.typed` marker — package ships type information to consumers (PEP 561).
- `__version__` exposed via `importlib.metadata` (single source of truth).
