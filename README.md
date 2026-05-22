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

Most RAG frameworks are anglo-centric and prototype-grade. `cenote` is built around three principles:

1. **Production-first** — eval, observability, audit trails built-in, not afterthoughts
2. **Opinionated** — one good stack, not twenty mediocre adapters
3. **LATAM-rooted** — Spanish embeddings, Mexican fiscal/regulated use cases, eval datasets in Spanish

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
uv run pytest -m "not integration"
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
