# cenote

Production-grade Python framework for building agentic RAG applications. Protocol-based, multi-tenant by design, type-strict from day one.

## Why cenote?

Most RAG frameworks are kitchen-sink — they ship 100+ integrations, every embedder, every store, every prompt template. They are great for prototyping and painful for production. cenote takes the opposite stance: a small set of well-designed primitives with no framework lock-in.

- **Protocol-based** — every primitive (`Chunker`, `Embedder`, `VectorStore`, `Retriever`) is a `typing.Protocol`. Implement the interface, plug it in. No inheritance hierarchies.
- **Multi-tenant by design** — `namespace` is a required argument on every store and retriever method. Cross-tenant leakage is impossible by construction.
- **Type-strict** — `mypy --strict` clean. `py.typed` shipped. Your IDE and CI catch wiring errors before runtime.
- **Production hardenings** — embedding batching with rate limiting, transactional upserts, idempotent migrations, dimension validation, structured logging. The boring stuff that matters.
- **LATAM-first roadmap** — Spanish-aware BM25, evaluation datasets in Spanish, fiscal/regulatory document support. M1.1+.

## What it is not

- **Not a LangChain alternative.** LangChain has 10+ engineers, ~100k stars, kitchen-sink breadth. cenote covers a deliberately narrow surface.
- **Not a full agent framework.** Agent primitives, LLM client wrappers, and observability adapters land in M1.1+. Today: chunking, embedding, storage, retrieval.

## Get started

→ [Quickstart](quickstart.md) — index a corpus and run a query in 5 minutes.
→ [API Reference](api/models.md) — every public symbol, auto-generated from docstrings.
→ [Architecture](architecture.md) — design rationale and runtime flow.

## License

[Apache 2.0](https://github.com/jovandyaz/pycenote/blob/main/LICENSE).
