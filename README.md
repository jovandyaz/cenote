# cenote

[![CI](https://github.com/jovandyaz/pycenote/actions/workflows/ci.yml/badge.svg)](https://github.com/jovandyaz/pycenote/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Production-grade Python framework for building agentic RAG applications. Multilingual-capable from day 1; Spanish/LATAM-first features (Spanish-aware BM25, ES evaluation datasets, fiscal/regulatory document support) on the M1.1+ roadmap.

> 🚧 **Early development.** APIs will change. Not yet on PyPI.

## What it is

`cenote` provides the building blocks for retrieval-augmented generation and agentic systems that need to ship to production: chunkers, embedders, vector stores, retrievers, rerankers, agent primitives, evaluation harnesses, and observability helpers.

Opinionated stack: Python 3.12+, Anthropic Claude, LangGraph, pgvector, Pydantic, Langfuse, DeepEval.

## Why

Most RAG frameworks are prototype-grade. `cenote` is built around three principles:

1. **Production-first** — eval, observability, audit trails built-in, not afterthoughts
2. **Opinionated** — one good stack, not twenty mediocre adapters
3. **Multilingual now, LATAM-focused next** — production embedders from Voyage AI and Cohere are multilingual out of the box; Spanish-specific tokenization, evaluation datasets, and Mexican fiscal/regulatory features land in M1.1+

The name comes from cenotes — natural deep wells in the Yucatán Peninsula used by the Maya as sacred sources of fresh water and knowledge. The metaphor maps to RAG: a deep, structured source of knowledge from which you retrieve context.

## Status

| Module | Status |
|---|---|
| chunkers | 🚧 in progress |
| embedders | 🚧 in progress |
| stores | 🚧 in progress |
| retrievers | 🚧 in progress |
| rerankers | ⏳ planned |
| llm | ⏳ planned |
| agents | ⏳ planned |
| eval | ⏳ planned |
| observability | ⏳ planned |

See [`docs/00-first-milestone.md`](docs/00-first-milestone.md) for the current milestone scope.

## Quickstart

```bash
git clone https://github.com/jovandyaz/pycenote.git
cd pycenote
uv sync

# Option 1 — run the demo with MockEmbedder (no API key)
uv run python demos/quickstart.py --provider mock

# Option 2 — run with Voyage AI (requires VOYAGE_API_KEY)
export VOYAGE_API_KEY=...
uv run python demos/quickstart.py --provider voyage

# Option 3 — run with Cohere multilingual (requires COHERE_API_KEY)
export COHERE_API_KEY=...
uv run python demos/quickstart.py --provider cohere
```

Sample output:

```text
=== Query: What is a cenote?
  1. [score=0.812] (Cenote) A cenote is a natural sinkhole that exposes groundwater beneath a limestone surface. Found mostly in the Yucatán Peninsul...
  2. [score=0.563] (Yucatán Peninsula) The Yucatán Peninsula is a landmass in southeastern Mexico and northern Central America. It is known for its ...

=== Query: What does RRF stand for?
  1. [score=0.798] (Reciprocal Rank Fusion) Reciprocal Rank Fusion (RRF) is a rank aggregation method that combines results from multiple ranked list...
  2. [score=0.541] (Hybrid search) Hybrid search combines sparse retrieval (e.g., BM25) with dense retrieval (vector search) to leverage the strengths...
```

## Downstream products

`cenote` is the shared core for two products in development:

- **knowtis-ai** — RAG and research agent for the [Knowtis](https://knowtis.ai) notes platform
- **cfdi-agent** — accounting reconciliation + CFDI 4.0 compliance agent for Mexican PYMEs

## Contributing

Early stage; not yet accepting external contributions. See [`CLAUDE.md`](CLAUDE.md) for conventions.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Author

Jovan Díaz — [github.com/jovandyaz](https://github.com/jovandyaz)
