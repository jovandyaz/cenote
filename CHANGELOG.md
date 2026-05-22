# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 disclaimer.** APIs may break in any minor release until `1.0.0` ships.
> Patch releases (`0.1.0` → `0.1.1`) are bug fixes only.

## [Unreleased]

### Added

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

## [0.1.0] - YYYY-MM-DD

### Added

- Initial project scaffolding: `uv`, `ruff`, `mypy --strict`, `pytest`, `pre-commit`,
  GitHub Actions CI (lint + type + unit tests, Python 3.12 & 3.13, `pip-audit`).
- `LICENSE` (Apache 2.0), `CHANGELOG.md`, `SECURITY.md`.
- `py.typed` marker — package ships type information to consumers (PEP 561).
- `__version__` exposed via `importlib.metadata` (single source of truth).
