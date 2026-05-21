# CLAUDE.md

This file is the persistent context for Claude Code sessions working on `cenote`. Read it at the start of every session.

## What this project is

`cenote` is a production-grade Python framework for building agentic RAG applications, with first-class support for Spanish-language content and Latin American use cases. It is the **shared core** for two downstream products that live in separate repos:

- **knowtis-ai** — RAG and research agent over the Knowtis notes platform
- **cfdi-agent** — accounting reconciliation + CFDI 4.0 compliance agent for Mexican PYMEs

Each downstream product validates the core from opposite ends: knowtis-ai needs creative synthesis, cfdi-agent needs deterministic correctness with audit trails. If the core serves both, it serves most production RAG verticals.

This repo (`pycenote`) contains the core library only. PyPI publication name will be `cenote-ai` (the bare `cenote` slot is occupied by an abandoned 2019 project).

## Tech stack

- **Python**: 3.12+
- **Package manager**: `uv` (use `uv sync`, `uv add`, `uv run ...`)
- **Linting & formatting**: `ruff` (replaces black, isort, flake8)
- **Type checking**: `mypy --strict`
- **Testing**: `pytest` + `pytest-asyncio` + `pytest-cov`
- **Data validation**: `pydantic` v2
- **Async**: default; sync only when wrapping inherently sync libraries
- **LLM provider**: Anthropic Claude (Sonnet 4.5 default, Opus for high-stakes reasoning)
- **Agent framework**: LangGraph (for state machines with conditional edges)
- **Vector store**: pgvector (Postgres extension)
- **Embeddings**: provider-agnostic protocol; concrete impl deferred (Voyage AI vs Cohere multilingual decision pending)
- **Observability**: Langfuse (self-hostable)
- **Evaluation**: DeepEval + custom metrics

## Project structure

```
pycenote/
├── src/cenote/
│   ├── chunkers/      # Text/markdown splitting
│   ├── embedders/     # Embedding providers (protocol + impls)
│   ├── stores/        # Vector stores (protocol + impls)
│   ├── retrievers/    # Retrieval strategies (BM25, vector, hybrid)
│   ├── rerankers/     # (future) Reranking strategies
│   ├── llm/           # (future) LLM client abstractions
│   ├── agents/        # (future) Agent primitives over LangGraph
│   ├── eval/          # (future) Eval harness
│   ├── observability/ # (future) Tracing helpers
│   ├── models.py      # Pydantic models (Document, Chunk, etc.)
│   └── types.py       # Shared type aliases
├── tests/             # Mirror src/cenote/ structure
├── docs/              # Milestone briefs and design docs
└── pyproject.toml
```

## Conventions

### Code style

- Type hints on everything public. `mypy --strict` must pass.
- Pydantic models for any data crossing module boundaries.
- Prefer `Protocol` over `ABC` for interfaces — duck typing + better composition.
- One class per concept per file. Avoid mega-modules.
- Async by default. Sync versions only where retrieval libraries force it.

### Naming

- Files and modules: `snake_case`
- Classes: `PascalCase`
- Protocols: just use the bare noun (`Chunker`, `Embedder`). Suffix with `Protocol` only when there's ambiguity with a concrete impl in the same module.
- Spanish identifiers are OK in domain-specific downstream code (`cfdi`, `rfc`, `iva`), never in this core repo.

### Tests

- One test file per source file. Mirror the path: `src/cenote/chunkers/markdown.py` ↔ `tests/chunkers/test_markdown.py`.
- Shared setup goes in `tests/conftest.py` or per-directory `conftest.py`.
- Integration tests (those requiring Postgres) go in `tests/integration/` and are marked `@pytest.mark.integration`.
- Aim for >80% coverage on `src/cenote/`.

### Commits

- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- Keep PRs focused. One sub-deliverable per PR (see `docs/00-first-milestone.md` for suggested breakdown).
- Branch naming: `feat/<short-desc>`, `fix/<short-desc>`, etc.

### Documentation

- Public functions/classes need docstrings (Google style).
- Module-level docstring explains the module's purpose in 1–2 lines.
- Examples in docstrings should be runnable.

## Commands

```bash
# Setup
uv sync                              # install all deps (incl. dev)

# Development
uv run pytest                        # all tests
uv run pytest tests/chunkers/        # subset
uv run pytest -m "not integration"   # skip integration tests
uv run pytest --cov=cenote           # with coverage
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run mypy src/                     # type check
uv run pre-commit run --all-files    # all checks

# Adding deps
uv add <package>                     # runtime dep
uv add --dev <package>               # dev dep

# Build
uv build                             # build wheel
```

## What to NOT do

- **Do not pull in LangChain** as a dependency. We use LangGraph (a focused subset) only. The LangChain mega-package is not wanted here.
- **Do not add concrete embedder implementations yet**. The `Embedder` protocol must stabilize first; the Voyage vs Cohere decision is pending.
- **Do not bake assumptions about Spanish-only**. The framework is LATAM-aware but multilingual. Default tokenizer/chunker choices must not be English-only.
- **Do not add framework-specific code** (FastAPI, Django, Flask, etc.) to `cenote` core. Those belong in downstream services that depend on `cenote`.
- **Do not commit secrets**. Use `.env` (gitignored) and `pydantic-settings`.
- **Do not skip type hints or tests** for "I'll add them later". Add them in the same PR or don't add the code.
- **Do not bypass the namespace parameter** on `VectorStore` / `Retriever` interfaces. Multi-tenancy is enforced at the protocol level.
- **Do not edit migrations** once committed. Add a new migration instead.

## Current focus

See `docs/00-first-milestone.md` for the active milestone scope. As of project start, we are building **M1.0 — Core Primitives**: chunkers, embedders, stores, retrievers.

Do NOT start work on agents, eval, or observability yet. Those depend on the primitives being stable.

## When in doubt

- Check `docs/` for design rationales
- Check existing implementations in the same module for patterns
- If introducing a new top-level dependency, propose it first (open a discussion or ask the maintainer)
- The maintainer is Jovan Díaz ([@jovandyaz](https://github.com/jovandyaz))
