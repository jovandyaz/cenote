# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 disclaimer.** APIs may break in any minor release until `1.0.0` ships.
> Patch releases (`0.1.0` → `0.1.1`) are bug fixes only.

## [Unreleased]

### Added

- `cenote.observability.SpanContext` Protocol: `set_attribute(k, v)` +
  `record_exception(e)`. `NoopSpanContext` is the no-op default.
- `cenote.embedders.cache.SqliteCache`: persistent `EmbeddingCache` backed by
  aiosqlite. Single-table schema, float32 BLOB storage (4× smaller than
  JSON, rounding error below cosine-similarity noise). `await
  SqliteCache.connect(path)` opens the file and applies the schema; composes
  with `CachedEmbedder` like any other cache. Runtime dep: `aiosqlite>=0.20`.

### Changed

- **BREAKING (pre-1.0)**: `Tracer.span()` now yields a `SpanContext` rather
  than `None`. Custom `Tracer` implementations must yield an object
  conforming to the `SpanContext` Protocol. Existing callers that use
  `async with tracer.span("op"): ...` (ignoring the yielded value) are
  unaffected.

## [0.2.0] - 2026-05-27

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
- `cenote.retrievers.HybridRetriever`: Reciprocal Rank Fusion over an
  arbitrary list of retrievers. Configurable per-retriever `weights`, RRF
  `k_constant` (default 60 per Cormack et al. 2009), and explicit
  `candidate_pool_size` (defaults to `max(limit * 4, 100)`) for tuning the
  candidate pool each base retriever fetches before fusion. Each base
  retriever runs in parallel via `asyncio.gather`; results dedup by `chunk.id`.
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
- `cenote.eval` bundled datasets: `load_miracl_es_subset()`,
  `load_miracl_en_subset()` (CC-BY-SA 3.0, see
  `src/cenote/eval/datasets/NOTICE.md`), and `load_cenote_mini_es()`
  (custom Spanish RAG-domain QA pairs, Apache 2.0). `EvalDataset` /
  `Query` dataclasses standardize loaders. Datasets ship in the wheel via
  hatch include rules.
- One-time `scripts/build_miracl_subset.py` for reproducible subsampling
  with `random.seed(42)`. Not shipped in the wheel.
- `cenote.eval.RetrievalBenchmark` + `BenchmarkResult`: orchestrator that
  runs any `Retriever` over an `EvalDataset` and emits aggregated and
  per-query `precision@k`, `recall@k`, and MRR. Doc-level matching against
  qrels (`chunk.document_id`). Works with vector, BM25, hybrid, and rerank
  pipelines.
- Dev dep: `deepeval>=2.0` recorded for upcoming DeepEval-specific
  evaluators in M1.2; the M1.1 bench harness is intentionally
  framework-agnostic.
- `scripts/run_baseline.py`: reproducible baseline runner — indexes any
  EvalDataset through `VoyageEmbedder + InMemoryVectorStore`, then runs
  five retrieval pipelines (vector, BM25, hybrid, hybrid+voyage-rerank,
  hybrid+cohere-rerank) through `RetrievalBenchmark`. Outputs JSON for
  copy-paste into the published baselines report.
- `docs/benchmarks/2026-05-27-m1-1-baselines.md`: M1.1 published baselines
  report. Ships with deferral language for the real numbers — full
  benchmark requires (a) successful MIRACL build (blocked by
  `datasets>=4` rejecting MIRACL's loader script) and (b) Voyage +
  Cohere API credentials. Both deferred to a 0.2.1 patch release; the
  retrieval stack itself is production-ready in 0.2.0.
- `docs/site/benchmarks.md` + `mkdocs.yml` nav entry: surfaces the
  benchmark report from the docs site.
- README link to the M1.1 baselines report.

### Changed

- `cenote.eval.metrics.{precision_at_k, recall_at_k, mean_reciprocal_rank}`
  accept an optional `key: Callable[[RetrievalResult], str]` parameter for
  extracting the comparison ID. Defaults to `chunk.id`. Used by
  `RetrievalBenchmark` to match against `chunk.document_id` at doc-level
  granularity without allocating a re-wrapped `Chunk` per result. Backwards
  compatible (positional/keyword args unchanged).
- `cenote.eval.EvalDataset.qrels` derived from `Query.relevant_doc_ids` in
  `__post_init__` rather than passed in at construction. Eliminates the
  parallel-data sync risk; `Query` is now the single source of truth for
  relevance judgments. Loader signature: `EvalDataset(name, language,
  documents, queries)`.

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
