# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 disclaimer.** APIs may break in any minor release until `1.0.0` ships.
> Patch releases (`0.1.0` → `0.1.1`) are bug fixes only.

## [0.6.2](https://github.com/jovandyaz/cenote/compare/v0.6.1...v0.6.2) (2026-06-07)


### Fixed

* **deps:** pin aiohttp&gt;=3.14 (2 CVEs via ir-datasets) ([1b66fa0](https://github.com/jovandyaz/cenote/commit/1b66fa0ac3402a36a55c2aa8369d853357512798))


### Documentation

* refresh status to v0.6.1 and current focus to M1.3 ([8297b5b](https://github.com/jovandyaz/cenote/commit/8297b5b3180b2840808ef9b480b959204ed1bcde))

## [0.6.1](https://github.com/jovandyaz/cenote/compare/v0.6.0...v0.6.1) (2026-06-02)


### Fixed

* **deps:** constrain lxml&gt;=6.1 to dodge cve pysec-2026-87 ([6ba01c8](https://github.com/jovandyaz/cenote/commit/6ba01c8e9f27b3682b50d5840055816dd677fd01))


### Changed

* **release-please:** trim verbose comments ([ccfcba4](https://github.com/jovandyaz/cenote/commit/ccfcba47ed7ca7326dbf861f1038e47eca331023))

## [0.6.0](https://github.com/jovandyaz/cenote/compare/v0.5.0...v0.6.0) (2026-05-31)


### Added

* **bench:** MIRACL-es harness with ranx metrics and Pyserini-2cr report ([c21fd96](https://github.com/jovandyaz/cenote/commit/c21fd96f6e8c93c0db385dbb1171c04327cd5cd9))
* **chunkers:** add Chunker protocol and RecursiveCharacterChunker ([49ad485](https://github.com/jovandyaz/cenote/commit/49ad485c4faf962c7ec3e2860d21e6bdd458006f))
* **coverage:** add PgVectorStore helper unit tests and Codecov upload (unit+integration flags) ([ff514d5](https://github.com/jovandyaz/cenote/commit/ff514d515feff8541e486ab71cd058632a838ea5))
* **demos:** add quickstart demo and README quickstart ([b79d3a6](https://github.com/jovandyaz/cenote/commit/b79d3a6249c126a4429023cf95428f37e2361ed9))
* **docs:** add mkdocs-material site with auto-generated API reference and GH Pages deploy ([1546afd](https://github.com/jovandyaz/cenote/commit/1546afde730ff0d06584be4633c9182b2636caef))
* **embedders:** add Embedder protocol and unit-norm MockEmbedder ([c112565](https://github.com/jovandyaz/cenote/commit/c1125655b74331422ce7f69a0d29f4fc3e019016))
* **embedders:** add EmbeddingCache protocol, InMemoryCache, CachedEmbedder ([71267c6](https://github.com/jovandyaz/cenote/commit/71267c6af1643551030852dff3d067db0968f44c))
* **embedders:** add VoyageEmbedder and CohereEmbedder (multilingual) ([1cbbc85](https://github.com/jovandyaz/cenote/commit/1cbbc856a1de01bde686ef5a2721175de9c06b8e))
* **errors:** add CenoteError hierarchy and replace bare ValueError raises ([ffdf25d](https://github.com/jovandyaz/cenote/commit/ffdf25daa24d4b82bc55c98ccb1bb400f1095c0c))
* **eval:** RetrievalBenchmark + bundled datasets + baseline scaffold (M1.1 phase 4) ([3269cf3](https://github.com/jovandyaz/cenote/commit/3269cf39235c1f2fd58873eec7148da5e6a8d3a3))
* **examples:** add custom_embedder and pgvector_setup cookbook examples ([73151dd](https://github.com/jovandyaz/cenote/commit/73151dd5b07b48a4f76de6c38381285d845cabec))
* future-API stubs (Reranker, Tracer, eval metrics) ([1718579](https://github.com/jovandyaz/cenote/commit/171857911d0e55a29984fa1162f743d065f40496))
* **llm:** LLMClient Protocol + AnthropicLLM with prompt caching (M1.2 phase 3+4) ([5b1336a](https://github.com/jovandyaz/cenote/commit/5b1336a61d5c58dfffde3955eb068c905dcc1887))
* **logging:** add structured logging across all cenote modules ([589b58a](https://github.com/jovandyaz/cenote/commit/589b58a0d420ef1366d76aea22c0002b9a2b9c98))
* M1.1 phase 1 — get_all_chunks, SpanishTokenizer, MarkdownChunker ([c1f4916](https://github.com/jovandyaz/cenote/commit/c1f4916f41508b5bbc29de53f725d021a10cadb0))
* M1.1 phase 2 — BM25Retriever + Voyage/Cohere rerankers via shared _HTTPReranker ([916ef42](https://github.com/jovandyaz/cenote/commit/916ef42cab69a1051507cc19fa20741f6fb5011b))
* M1.2 phase 1 — Tracer Protocol v2 + SqliteCache with WAL + set_many bulk API ([761d98b](https://github.com/jovandyaz/cenote/commit/761d98b087c2b178c5f29f805a428ea418612432))
* **models:** add Document, Chunk, EmbeddedChunk, RetrievalResult ([9bb50df](https://github.com/jovandyaz/cenote/commit/9bb50df751deb097e0364376c4a254bb997627f9))
* **observability:** OTel + Langfuse adapters + Traced wrappers (M1.2 phase 2) ([f17b4bc](https://github.com/jovandyaz/cenote/commit/f17b4bc3bc64d7ec8e0f800d45d7429e0a5e96e9))
* phase 4 primitives — TracedVectorStore + IndexingPipeline ([7679b89](https://github.com/jovandyaz/cenote/commit/7679b89381e7d856042076f7dc5cd74cb8fb72fc))
* project scaffolding (uv, ruff, mypy, pytest, pre-commit, CI matrix, Apache-2.0) ([fe8951c](https://github.com/jovandyaz/cenote/commit/fe8951c8c837b333bb30a55fe91bb00f8172090f))
* **release:** add PyPI release workflow with OIDC trusted publishing ([e4a5086](https://github.com/jovandyaz/cenote/commit/e4a5086419e5677871928381f4c68dadbdf11fa6))
* **retrievers:** add Retriever protocol and VectorRetriever ([00c4d8c](https://github.com/jovandyaz/cenote/commit/00c4d8c6e84a3ade16bb2649c559a49f29456f64))
* **retrievers:** HybridRetriever with Reciprocal Rank Fusion (M1.1 phase 3) ([6bf94dc](https://github.com/jovandyaz/cenote/commit/6bf94dc779813c33a5e9a6687f9a719acc3799f9))
* **stores:** add PgVectorStore with transactions, migrations tracking, HNSW tuning, CI integration job ([986c861](https://github.com/jovandyaz/cenote/commit/986c861d6d4201aacdba6359177cc3348ff60ba3))
* **stores:** add VectorStore protocol and InMemoryVectorStore ([280cf10](https://github.com/jovandyaz/cenote/commit/280cf1078fc1788d70fba0dadd4cdeb687e05b2c))
* **types:** add cenote.types aliases and adopt Vector in public signatures ([969ea4b](https://github.com/jovandyaz/cenote/commit/969ea4be5ce61b22df0ec02471e5bc1b8fe71ded))


### Fixed

* **ci:** adapt migrations test to read disk + drop pycenote from pip-audit ([8b85f51](https://github.com/jovandyaz/cenote/commit/8b85f5163c8f6ba1ae4a4b533ae7a6f1e43a33b8))
* **ci:** isolated venv for release verify + auto-enable GH Pages in docs deploy ([35a91cf](https://github.com/jovandyaz/cenote/commit/35a91cf6cbb8807b8a2b07eafbb811a42b3fdd77))
* **ci:** unblock CI on main (lint import order, pip-audit hashed deps, pgvector PK) ([4835281](https://github.com/jovandyaz/cenote/commit/4835281fae98b1f8fdc475ae199b6611bdec0051))
* **ci:** use uv export --no-emit-project to exclude pycenote from pip-audit ([787303d](https://github.com/jovandyaz/cenote/commit/787303d0cd0755f6a0e509e42ac374bc2807b8a3))
* **compose:** pin project name to cenote (was deriving from dir) ([b9f5b66](https://github.com/jovandyaz/cenote/commit/b9f5b66deee0ae708a38ca1917de3a6006a7b04d))
* **embedders:** honor Retry-After header, raise default max_retries to 6 ([e867653](https://github.com/jovandyaz/cenote/commit/e8676538fe981eb39d883466e470f7a019cfa054))
* phase 4 bug fixes — HNSW tx wrap, hybrid resilience, BM25 LRU+invalidate ([fedf797](https://github.com/jovandyaz/cenote/commit/fedf7972d6e0862c475f126ebbf1fe3ed465ff5e))
* **tokenizers:** make SpanishTokenizer pickle-safe via __getstate__ ([c734dfa](https://github.com/jovandyaz/cenote/commit/c734dfa228d6dd90166c71c9963e7ded485d190b))
* **verify:** correct grep pattern in phase2.sh check 3 (pytest --quiet output) ([4c91dcc](https://github.com/jovandyaz/cenote/commit/4c91dcc679ee5068d26a15657b6cba9da7abe5cb))
* **verify:** remove hardcoded user PATH from phase verify scripts ([154c960](https://github.com/jovandyaz/cenote/commit/154c960b235f32ee355b92c526f91d4bfc45f23c))


### Changed

* phase 4 retry+rate-limit — stamina with jitter + aiolimiter wrapper ([30fccf2](https://github.com/jovandyaz/cenote/commit/30fccf24aa4c1c9769d29544fafd8f7de764b6c1))


### Documentation

* add CONTRIBUTING.md with dev setup and release process ([7ae078e](https://github.com/jovandyaz/cenote/commit/7ae078e628f92a4a2f54506f5e2b40ae2acfe22e))
* **adrs:** add foundational ADRs 0001-0008 ([05e8558](https://github.com/jovandyaz/cenote/commit/05e8558b2297436fbca19ec881452b32754d8b3e))
* **adrs:** document release-please PR-create prerequisite in 0005 ([0c1dc7d](https://github.com/jovandyaz/cenote/commit/0c1dc7d957c30020fe499fd3d1b0930f8e77cf47))
* **adrs:** document v0.4.0 release lessons in 0005 ([2b9e362](https://github.com/jovandyaz/cenote/commit/2b9e362b1ac24f6d74f5d5eb6a010d430a16a8e5))
* **adrs:** expand 0008 monorepo with bench/rerankers/llm packages ([1514bc9](https://github.com/jovandyaz/cenote/commit/1514bc9f3d81bf2d1ee35d28ccb3a8ae91e0b01c))
* **adrs:** note Phase 1 corrections (OSV reusable wf, Sigstore auto via pypa-publish) ([4cacf97](https://github.com/jovandyaz/cenote/commit/4cacf97b0c80c3cc0873f1361bf94ef159384932))
* **adrs:** note Phase 3 mike deferral to Phase 5 in ADR-0004 ([88815b8](https://github.com/jovandyaz/cenote/commit/88815b851754138fc743bfd35eb82a55d9dfc6b2))
* **adrs:** phase 5 implementation notes in 0004 and 0005 ([2d0c9d3](https://github.com/jovandyaz/cenote/commit/2d0c9d3a03d27a517224e8b1b8997bc4381a8355))
* **bench:** add ADR-0009 + benchmarks.md scaffold + README row ([c2c77d2](https://github.com/jovandyaz/cenote/commit/c2c77d2b8f04a2d08ba8977bcd96a786acf910d1))
* **changelog:** expand SqliteCache entry with WAL + set_many ([63a4832](https://github.com/jovandyaz/cenote/commit/63a4832d6f3344785ba8ebbdcf3bb3ee5138bb59))
* **changelog:** record M1.0 future-API stubs entries ([9b2f774](https://github.com/jovandyaz/cenote/commit/9b2f774ad63f7376839d920cc2b39cbcc7db4e54))
* **milestone:** mark M1.0 closed with acceptance criteria and deliverables note ([9f11e58](https://github.com/jovandyaz/cenote/commit/9f11e585ec89a6e9c46f6e44453e12edcb315333))
* phase 3 — Definition of Done + ADRs index pages in mkdocs nav ([f8f80d3](https://github.com/jovandyaz/cenote/commit/f8f80d39e77514c5b60a0e628eebbdd69aacc008))
* **plan:** add diagrams and skip other docs ([e4516b3](https://github.com/jovandyaz/cenote/commit/e4516b367ada6d38b4c69bf488d050a9836e663e))
* project context, milestone brief, implementation plan, claude code config ([793100d](https://github.com/jovandyaz/cenote/commit/793100dc9d26231c0f3bde0e695af6e5b5a8f13b))
* **proofs:** add phase 4 + 5 practical proof report ([a09fa7e](https://github.com/jovandyaz/cenote/commit/a09fa7ec9d50b8b7acddf25632a87c354c00203a))
* **proofs:** add v0.4.0 ship report ([71d482b](https://github.com/jovandyaz/cenote/commit/71d482b1289d9c972420d7d1b51b9128e3fb14f7))
* refresh README to v0.5.0 + add internal docs ([b09f664](https://github.com/jovandyaz/cenote/commit/b09f664cd401fb383ee4522a707bc5205b7b2f2f))
* rewrite README with positioning, module status, extension guide, and roadmap ([fc9a973](https://github.com/jovandyaz/cenote/commit/fc9a97342329ac2152efabeecae17dd408c23cea))

## [0.5.0](https://github.com/jovandyaz/cenote/compare/v0.4.1...v0.5.0) (2026-05-29)


### Added

* **bench:** MIRACL-es harness with ranx metrics and Pyserini-2cr report ([8fdbbb2](https://github.com/jovandyaz/cenote/commit/8fdbbb29b0606eaa86a5d4465baf3a46976d8bf4))

## [0.4.1](https://github.com/jovandyaz/cenote/compare/v0.4.0...v0.4.1) (2026-05-29)


### Fixed

* **embedders:** honor Retry-After header, raise default max_retries to 6 ([c8d5880](https://github.com/jovandyaz/cenote/commit/c8d5880e71154a863f259acaf1c9c113bf8c835a))
* **tokenizers:** make SpanishTokenizer pickle-safe via __getstate__ ([8c98598](https://github.com/jovandyaz/cenote/commit/8c9859821a0711b551e39f7eed3fdc051092be87))


### Documentation

* **adrs:** document v0.4.0 release lessons in 0005 ([631ed25](https://github.com/jovandyaz/cenote/commit/631ed252546f66bd6261f713a9334c64d8c64d85))
* **proofs:** add v0.4.0 ship report ([e807fe3](https://github.com/jovandyaz/cenote/commit/e807fe319c679850f83462ff295c9cdc36d25407))

## [0.4.0](https://github.com/jovandyaz/cenote/compare/v0.3.0...v0.4.0) (2026-05-29)


### Added

* phase 4 primitives — TracedVectorStore + IndexingPipeline ([7679b89](https://github.com/jovandyaz/cenote/commit/7679b89381e7d856042076f7dc5cd74cb8fb72fc))


### Fixed

* **compose:** pin project name to cenote (was deriving from dir) ([b9f5b66](https://github.com/jovandyaz/cenote/commit/b9f5b66deee0ae708a38ca1917de3a6006a7b04d))
* phase 4 bug fixes — HNSW tx wrap, hybrid resilience, BM25 LRU+invalidate ([fedf797](https://github.com/jovandyaz/cenote/commit/fedf7972d6e0862c475f126ebbf1fe3ed465ff5e))
* **verify:** correct grep pattern in phase2.sh check 3 (pytest --quiet output) ([4c91dcc](https://github.com/jovandyaz/cenote/commit/4c91dcc679ee5068d26a15657b6cba9da7abe5cb))
* **verify:** remove hardcoded user PATH from phase verify scripts ([154c960](https://github.com/jovandyaz/cenote/commit/154c960b235f32ee355b92c526f91d4bfc45f23c))


### Changed

* phase 4 retry+rate-limit — stamina with jitter + aiolimiter wrapper ([30fccf2](https://github.com/jovandyaz/cenote/commit/30fccf24aa4c1c9769d29544fafd8f7de764b6c1))


### Documentation

* **adrs:** add foundational ADRs 0001-0008 ([05e8558](https://github.com/jovandyaz/cenote/commit/05e8558b2297436fbca19ec881452b32754d8b3e))
* **adrs:** document release-please PR-create prerequisite in 0005 ([0c1dc7d](https://github.com/jovandyaz/cenote/commit/0c1dc7d957c30020fe499fd3d1b0930f8e77cf47))
* **adrs:** note Phase 1 corrections (OSV reusable wf, Sigstore auto via pypa-publish) ([4cacf97](https://github.com/jovandyaz/cenote/commit/4cacf97b0c80c3cc0873f1361bf94ef159384932))
* **adrs:** note Phase 3 mike deferral to Phase 5 in ADR-0004 ([88815b8](https://github.com/jovandyaz/cenote/commit/88815b851754138fc743bfd35eb82a55d9dfc6b2))
* **adrs:** phase 5 implementation notes in 0004 and 0005 ([2d0c9d3](https://github.com/jovandyaz/cenote/commit/2d0c9d3a03d27a517224e8b1b8997bc4381a8355))
* phase 3 — Definition of Done + ADRs index pages in mkdocs nav ([f8f80d3](https://github.com/jovandyaz/cenote/commit/f8f80d39e77514c5b60a0e628eebbdd69aacc008))
* **proofs:** add phase 4 + 5 practical proof report ([a09fa7e](https://github.com/jovandyaz/cenote/commit/a09fa7ec9d50b8b7acddf25632a87c354c00203a))

## [Unreleased]

### Added

- (none yet)

## [0.3.0] - 2026-05-27

### Added

- `cenote.observability.SpanContext` Protocol: `set_attribute(k, v)` +
  `record_exception(e)`. `NoopSpanContext` is the no-op default.
- `cenote.embedders.cache.SqliteCache`: persistent `EmbeddingCache` backed by
  aiosqlite. Single-table schema, float32 BLOB storage (4x smaller than
  JSON, rounding error below cosine-similarity noise), WAL journal mode +
  `synchronous=NORMAL` for ~10x batch-write throughput. Supports `async
  with` via `__aenter__`/`__aexit__`. Composes with `CachedEmbedder` like
  any other cache. Runtime dep: `aiosqlite>=0.20`.
- `EmbeddingCache.set_many(items)`: bulk-write API on the Protocol. Persistent
  backends batch into a single transaction; `CachedEmbedder.embed()` uses
  it on the miss path so an N-chunk batch is one fsync, not N.
- `cenote.observability.otel.OTelTracer` + `OTelSpanContext`: adapter
  bridging the `Tracer` Protocol to `opentelemetry.trace.Tracer`. Install
  with `pip install cenote-core[otel]`. Without the extra, import raises a
  clear `ImportError`. Optional dep: `opentelemetry-api>=1.27`,
  `opentelemetry-sdk>=1.27`.
- `cenote.observability.langfuse.LangfuseTracer` + `LangfuseSpanContext`:
  adapter bridging the `Tracer` Protocol to a `langfuse.Langfuse` client.
  Spans with the `llm.` prefix create `generation` observations (carry
  token/model metadata via `gen_ai.*` attribute mapping); other spans
  create plain `span` observations. Install with
  `pip install cenote-core[langfuse]`. Optional dep: `langfuse>=2.0`.
- `cenote.observability.wrappers.{TracedEmbedder, TracedRetriever,
  TracedReranker}`: composition-pattern wrappers that emit spans for any
  Embedder/Retriever/Reranker impl without modifying existing classes
  (OCP). Use `TracedEmbedder(VoyageEmbedder(...), tracer)` to opt in. Emits
  spans `embedder.embed`, `retriever.retrieve`, `reranker.rerank` with
  `gen_ai.*` attributes where relevant.
- `cenote.llm.LLMClient` Protocol with async `complete()` + `stream()`,
  plus `NoopLLM` default for tests. Conversation turns use a new
  `cenote.models.Message` Pydantic v2 model (`role`, `content`, optional
  `cache_control="ephemeral"` for Anthropic prompt caching).
- `cenote.errors.LLMError`: new exception class for non-rate-limit LLM
  failures.
- `cenote.llm.AnthropicLLM`: production-grade Anthropic Claude client.
  `complete()` returns the assistant text, `stream()` yields deltas in
  arrival order. Native prompt caching via `Message(cache_control="ephemeral")`
  markers. Tracer-aware (`tracer=` ctor kwarg; defaults to NoopTracer).
  Spans `llm.complete`/`llm.stream` emit `gen_ai.*` attributes including
  `cache_read_input_tokens` and `cache_creation_input_tokens` for cost
  tracking. Runtime dep: `anthropic>=0.39`.

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
