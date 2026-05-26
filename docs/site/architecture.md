# Architecture

cenote is layered around three protocols and a small set of value types. The layout below shows what is in `src/cenote/` today and how the pieces compose.

## Diagrams

Three diagrams document the system at different zoom levels:

- [**Ecosystem**](https://github.com/jovandyaz/cenote/blob/main/docs/diagrams/01-ecosystem.drawio) — cenote's position in the wider RAG ecosystem (LangChain, LlamaIndex, vector DBs, embedding providers).
- [**Internal architecture**](https://github.com/jovandyaz/cenote/blob/main/docs/diagrams/02-architecture.drawio) — the 5 layers (`models`, `chunkers`, `embedders`, `stores`, `retrievers`) + future-API stubs, with Protocol vs implementation vs data model distinguished.
- [**Runtime flow**](https://github.com/jovandyaz/cenote/blob/main/docs/diagrams/03-runtime-flow.drawio) — sequence diagram of the indexing path and query path, showing batching, rate limiting, transactions, and HNSW tuning.

GitHub renders `.drawio` files inline natively (since 2024). Click any link above to view.

## Key design choices

### Multi-tenancy at the protocol level

`namespace: str` is mandatory on every method of `VectorStore` and `Retriever`. There is no default; there is no way to query "across all namespaces". This makes cross-tenant leakage a compile-time error rather than a runtime risk.

### Composition over inheritance

Concrete classes (`MockEmbedder`, `VoyageEmbedder`, `InMemoryVectorStore`, etc.) don't inherit from the protocols — they satisfy them structurally. This means you can drop in any class with the right shape, including ones that wrap third-party SDKs.

### Hardenings built in

- Embedding batching honors per-provider limits (Voyage ≤128/req, Cohere ≤96/req)
- `RateLimiter` is sliding-window, lock-coordinated across asyncio tasks
- `PgVectorStore.upsert` wraps in `conn.transaction()` — partial-batch failure rolls back
- Migrations tracked in `cenote_schema_migrations` table — `apply_migrations()` is idempotent
- `MockEmbedder` returns unit-norm vectors (matches Voyage/Cohere distribution; avoids concentration-of-measure footguns in tests)
- `CachedEmbedder` slot-array preserves input order across cache hits and misses

### What is deliberately missing

LLM client wrappers, agent primitives, observability adapters, and reranker implementations are M1.1+ work. M1.0 ships the indexing and retrieval primitives only.
