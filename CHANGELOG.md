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

## [0.1.0] - YYYY-MM-DD

### Added

- Initial project scaffolding: `uv`, `ruff`, `mypy --strict`, `pytest`, `pre-commit`,
  GitHub Actions CI (lint + type + unit tests, Python 3.12 & 3.13, `pip-audit`).
- `LICENSE` (Apache 2.0), `CHANGELOG.md`, `SECURITY.md`.
- `py.typed` marker — package ships type information to consumers (PEP 561).
- `__version__` exposed via `importlib.metadata` (single source of truth).
