# Milestone M1.0 — Core Primitives

> **Goal**: Establish the foundational abstractions and one or two implementations for each, with full test coverage. No agents, no LLM calls, no observability layer yet. Just the primitives every downstream module will use.

## Scope

Implement, with tests:

1. **Data models** (`src/cenote/models.py`)
2. **Chunker** protocol + 2 implementations
3. **Embedder** protocol + caching wrapper + mock impl (no concrete provider impl yet)
4. **VectorStore** protocol + pgvector implementation
5. **Retriever** protocol + 3 implementations (BM25, vector, hybrid)

Also:

- Project scaffolding (`pyproject.toml`, `ruff` config, `mypy` config, `pytest` config, pre-commit)
- CI workflow (GitHub Actions): lint + type check + unit tests on PR
- `README.md` and `CLAUDE.md` (already done)
- `docker-compose.test.yml` for the integration tests

## Out of scope for M1.0

- Concrete embedder implementations (Voyage, Cohere) — deferred to M1.1
- Rerankers
- LLM client wrappers
- Agent framework
- Evaluation harness
- Observability/tracing
- Documentation site (markdown in `docs/` only for now)

---

## Detailed specs

### 1. Data models — `src/cenote/models.py`

Pydantic v2 models. Treat these as the contracts between every module.

```python
class Document(BaseModel):
    """Source document before chunking."""
    id: str                                          # caller-provided unique ID
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None                        # e.g., URL, file path, note ID

class Chunk(BaseModel):
    """Output of a Chunker. The atomic embeddable unit."""
    id: str                                          # deterministic from document_id + position
    document_id: str
    content: str
    position: int                                    # ordering within the source document
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str                                # SHA-256 of content; used as embedding cache key

class EmbeddedChunk(BaseModel):
    """A Chunk together with its embedding vector."""
    chunk: Chunk
    embedding: list[float]
    embedding_model: str                             # format: "provider:model_id" e.g. "voyage:voyage-3-large"
    dimensions: int

class RetrievalResult(BaseModel):
    """Output of a Retriever."""
    chunk: Chunk
    score: float                                     # higher = more relevant
    retriever: str                                   # which retriever produced this ("bm25", "vector", "hybrid")
```

Tests:

- `content_hash` is computed correctly (SHA-256 hex of `chunk.content`)
- Chunk IDs are deterministic given the same `(document_id, position)` — provide a helper `Chunk.make_id(document_id, position) -> str`
- Models reject extra fields by default (`model_config = ConfigDict(extra="forbid")`)

### 2. Chunker — `src/cenote/chunkers/`

#### Protocol — `chunkers/base.py`

```python
from typing import Protocol
from cenote.models import Chunk, Document

class Chunker(Protocol):
    """Splits a Document into Chunks."""

    def chunk(self, document: Document) -> list[Chunk]:
        ...
```

#### a) `RecursiveCharacterChunker` — `chunkers/recursive.py`

- Splits on a list of separators in priority order: `["\n\n", "\n", ". ", " ", ""]`
- Configurable: `chunk_size: int = 512`, `chunk_overlap: int = 50`
- Tries to keep chunks under `chunk_size`; falls back to the next separator when oversize
- Sets `metadata` to a copy of `document.metadata`
- Each chunk's `content_hash` matches `sha256(chunk.content)`

Tests:

- Empty document → empty list
- Short document (under chunk_size) → single chunk
- Long document → multiple chunks of approximately chunk_size
- Verifies overlap between consecutive chunks
- Verifies `content_hash` is deterministic and matches SHA-256
- Chunk positions are sequential `0, 1, 2, ...`

#### b) `MarkdownChunker` — `chunkers/markdown.py`

- Respects markdown structure: headers, code blocks, lists
- Never splits inside a fenced code block (```)
- Prefers splitting on headers (`#`, `##`, `###`, etc.)
- Each chunk includes the heading hierarchy in `metadata["headings"]: list[str]` (e.g., `["Section 1", "Subsection 1.1"]`)
- Falls back to recursive splitting within sections that exceed `chunk_size`

Tests:

- Doc with H1 + 2× H2 → at least 3 chunks aligned to headers
- Code blocks not split mid-block (test with a long code block that exceeds chunk_size)
- Heading context propagated correctly to metadata
- Doc with no markdown structure behaves like RecursiveCharacterChunker

### 3. Embedder — `src/cenote/embedders/`

#### Protocol — `embedders/base.py`

```python
from typing import Protocol
from cenote.models import Chunk, EmbeddedChunk

class Embedder(Protocol):
    """Generates embedding vectors for chunks and queries."""

    @property
    def model_id(self) -> str:
        """Format: 'provider:model_name', e.g., 'voyage:voyage-3-large'."""
        ...

    @property
    def dimensions(self) -> int:
        ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Embed chunks. Returns EmbeddedChunks in the same order as input."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        ...
```

#### Cache protocol — `embedders/cache.py`

```python
class EmbeddingCache(Protocol):
    async def get(self, model_id: str, content_hash: str) -> list[float] | None: ...
    async def set(self, model_id: str, content_hash: str, embedding: list[float]) -> None: ...
```

#### `InMemoryCache` — `embedders/cache.py`

Simple dict-backed implementation. Useful for tests and small-scale usage.

#### `CachedEmbedder` — `embedders/cache.py`

Decorates any `Embedder` with an `EmbeddingCache`:

- On `embed()`: checks cache per chunk by `(model_id, chunk.content_hash)`; only sends cache misses to the underlying embedder; merges results preserving input order
- Forwards `model_id`, `dimensions`, `embed_query` to the underlying embedder

Tests:

- Cache hit avoids the underlying embedder call (use a mock embedder with a call counter)
- Cache miss invokes embedder and stores the result
- Mixed batch (some hits, some misses) preserves input order
- Different `model_id`s produce different cache keys (so the same chunk re-embeds when the model changes)

#### `MockEmbedder` — `embedders/mock.py`

Returns deterministic vectors derived from `chunk.content_hash` (e.g., seed a PRNG with the hash, produce a vector of configured dimensions). Useful for:

- Unit tests of components that need an Embedder without API calls
- Smoke tests without API keys

Lives in `src/` (not just tests) so downstream products can also use it for their own tests.

### 4. VectorStore — `src/cenote/stores/`

#### Protocol — `stores/base.py`

```python
from typing import Any, Protocol
from cenote.models import EmbeddedChunk, RetrievalResult

class VectorStore(Protocol):
    async def upsert(
        self,
        embedded_chunks: list[EmbeddedChunk],
        namespace: str,
    ) -> None:
        ...

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        ...

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        ...

    async def delete_namespace(self, namespace: str) -> None:
        ...
```

**Multi-tenant isolation is enforced by the protocol**: `namespace` is required on every method. Never query without it.

#### `PgVectorStore` — `stores/pgvector.py`

- Uses `asyncpg` for connection pooling
- Single table schema:

  ```sql
  CREATE TABLE cenote_chunks (
      id            TEXT PRIMARY KEY,
      namespace     TEXT NOT NULL,
      document_id   TEXT NOT NULL,
      content       TEXT NOT NULL,
      metadata      JSONB NOT NULL DEFAULT '{}',
      embedding     vector(N) NOT NULL,
      embedding_model TEXT NOT NULL,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  );

  CREATE INDEX cenote_chunks_namespace_doc_idx ON cenote_chunks (namespace, document_id);
  CREATE INDEX cenote_chunks_embedding_hnsw_idx ON cenote_chunks
      USING hnsw (embedding vector_cosine_ops);
  ```

- `N` (dimensions) is set at construction time. Cannot mix dimensions in one store instance.
- Configurable similarity: cosine (default), L2, inner product
- Schema migrations live in `src/cenote/stores/pgvector_migrations/` as numbered SQL files (`001_init.sql`, etc.). Provide a helper `apply_migrations(conn)`.

Integration tests:

- Use a Postgres container via `docker-compose.test.yml` (image: `pgvector/pgvector:pg16`)
- Marked `@pytest.mark.integration`
- CI runs them in a separate job that spins up the container
- Cover: upsert + search round-trip, namespace isolation (data in namespace A is invisible from namespace B), filter on metadata, deletion

### 5. Retriever — `src/cenote/retrievers/`

#### Protocol — `retrievers/base.py`

```python
from typing import Any, Protocol
from cenote.models import RetrievalResult

class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        ...
```

#### a) `VectorRetriever` — `retrievers/vector.py`

- Composes an `Embedder` and a `VectorStore`
- `retrieve()`: calls `embedder.embed_query()`, then `store.search()`, returns the results with `retriever="vector"`

#### b) `BM25Retriever` — `retrievers/bm25.py`

- Pure lexical retrieval via the `rank_bm25` library
- In-memory index, scoped per-namespace
- Loads chunk text from the `VectorStore` on first use per namespace (cache the loaded chunks for the lifetime of the retriever instance)
- For tests, provide a constructor that accepts pre-loaded chunks directly
- Returns `RetrievalResult` with `retriever="bm25"`

#### c) `HybridRetriever` — `retrievers/hybrid.py`

- Composes a `VectorRetriever` and a `BM25Retriever`
- Fuses results via Reciprocal Rank Fusion (RRF), default `k=60`
- Configurable weights per retriever (default 1.0 each)
- Returns deduplicated, score-fused results with `retriever="hybrid"`
- Pseudocode:

  ```
  for each result in vector_results (rank r): score += weight_v / (k + r)
  for each result in bm25_results   (rank r): score += weight_b / (k + r)
  return top-N by combined score
  ```

Tests for each retriever:

- Results sorted by `score` descending
- Namespace isolation verified (results never include chunks from other namespaces)
- Empty corpus → empty results
- HybridRetriever: a chunk present only in vector results still appears in output; ranking changes when weights change

---

## Acceptance criteria

- [ ] `uv sync && uv run pytest -m "not integration"` passes from a clean checkout
- [ ] `docker compose -f docker-compose.test.yml up -d && uv run pytest -m integration` passes
- [ ] `uv run ruff check .` and `uv run ruff format --check .` clean
- [ ] `uv run mypy src/` clean in `--strict` mode
- [ ] Coverage on `src/cenote/` > 80%
- [ ] CI workflow runs lint + type check + unit tests on every PR, integration tests on PRs to `main`
- [ ] All public symbols have docstrings
- [ ] No `# type: ignore` comments without an accompanying explanatory comment

## Suggested PR breakdown

To keep changes reviewable, ship in this order. Each PR is self-contained and mergeable independently after #1.

1. **Scaffolding** — `pyproject.toml`, ruff/mypy/pytest configs, `.gitignore`, `.pre-commit-config.yaml`, CI workflow, empty `src/cenote/__init__.py`
2. **Data models** — `models.py` + tests
3. **Chunker protocol + RecursiveCharacterChunker** + tests
4. **MarkdownChunker** + tests
5. **Embedder protocol + MockEmbedder** + tests
6. **EmbeddingCache + InMemoryCache + CachedEmbedder** + tests
7. **VectorStore protocol + PgVectorStore + migrations + docker-compose.test.yml + integration tests**
8. **VectorRetriever** + tests
9. **BM25Retriever** + tests
10. **HybridRetriever** + tests

## Design rationale

### Why Protocol over ABC

- Better composition: any object with the right methods works, no inheritance hierarchy required
- Plays nicely with mocks in tests
- Modern Python idiom; `typing.Protocol` is the recommended way to express duck-typed interfaces

### Why caching is a wrapper, not built into each embedder

- Single Responsibility: an embedder embeds, a cache caches
- Lets us swap cache backends (in-memory, Redis, Postgres) independently
- Easy to disable caching for one-off runs or testing
- Easier to unit-test caching logic in isolation

### Why `namespace` is at the protocol level

- Multi-tenancy is a first-class concern for both downstream products (per-user in knowtis-ai, per-cliente in cfdi-agent)
- Forcing namespace as a parameter prevents accidental cross-tenant queries
- Each tenant maps to a namespace; cleanly avoids the schema-per-tenant antipattern at small scale

### Why BM25 + vector hybrid

- Vector search excels at semantic similarity but misses exact-term matches
- BM25 catches proper nouns, IDs, codes, and rare terms that vectors lose
- RRF fusion is parameter-free and robust (no need to tune score scaling between retrievers)
- Most production RAG systems converge on hybrid retrieval

## References

- Recursive character splitting: LangChain's `RecursiveCharacterTextSplitter` (algorithm only, we are NOT importing LangChain)
- pgvector docs: <https://github.com/pgvector/pgvector>
- Reciprocal Rank Fusion: Cormack, Clarke, Buettcher (SIGIR 2009)
- BM25 implementation: `rank_bm25` on PyPI

## Next milestone preview

**M1.1** (do NOT start yet, listed only for context):

- First concrete `Embedder` implementation — Voyage AI or Cohere multilingual (decision pending after M1.0 ships)
- `Reranker` protocol + Cohere/Voyage rerank implementation
- Eval harness skeleton (DeepEval integration + custom metrics for retrieval quality)
- Langfuse observability hooks
