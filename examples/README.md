# Examples

Two runnable examples that demonstrate the patterns most users need.

| File | Demonstrates | Requires |
|---|---|---|
| `custom_embedder.py` | Implementing the `Embedder` protocol via structural typing — no inheritance | None (no API keys, no Docker) |
| `pgvector_setup.py` | Production setup with `PgVectorStore` — connect, apply migrations, multi-tenant indexing, namespace isolation | Postgres with pgvector (use `docker-compose.test.yml`) |

## Run

### Custom embedder

```bash
uv run python examples/custom_embedder.py
```

### Pgvector setup

```bash
docker compose -f docker-compose.test.yml up -d
uv run python examples/pgvector_setup.py
docker compose -f docker-compose.test.yml down -v
```

## What's deliberately NOT here

The cookbook is intentionally small. We do not ship examples for:

- Voyage / Cohere usage — already covered by `demos/quickstart.py --provider voyage|cohere`
- Reranking — `Reranker` protocol exists but has no concrete impl yet (M1.1+)
- Streaming embed — out of scope for M1.0 (M1.1+)
- Persistent embedding cache — `InMemoryCache` is the only cache today (M1.1+)

When those land, examples will follow.
