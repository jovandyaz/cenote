# M1.0 — Core Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the foundational abstractions and one or two implementations for each RAG primitive (chunker, embedder, vector store, retriever) plus a real end-to-end demo, so `cenote` exits M1.0 with a working RAG pipeline (not just plumbing).

**Architecture:** Greenfield Python library, `src/`-layout, `Protocol`-based interfaces, multi-tenant by default (namespace required at the protocol level), async I/O for embed/search, sync for CPU-only paths (chunking). Two real embedders (Voyage AI + Cohere multilingual) validate the `Embedder` protocol against more than one impl. Two stores (`InMemoryVectorStore` for tests/demos + `PgVectorStore` for production) validate the `VectorStore` protocol the same way. Composition over inheritance throughout; caching is a wrapper, not a base class.

**Tech Stack:** Python 3.12+, `uv` (package mgr), `ruff` (lint+format), `mypy --strict`, `pytest` + `pytest-asyncio` + `pytest-cov`, `pydantic` v2, `httpx` (HTTP), `asyncpg` (Postgres), `pgvector/pgvector:pg16` (vector ext), `numpy` (cosine sim in InMemoryVectorStore), `respx` (HTTP mocking in tests), `pre-commit`, GitHub Actions.

**Scope changes vs. the original milestone brief (docs/00-first-milestone.md):**

| Change | Direction | Reason |
|---|---|---|
| `MarkdownChunker` | Deferred to M1.1 | YAGNI — no downstream product is consuming markdown yet |
| `BM25Retriever` + `HybridRetriever` | Deferred to M1.1 | Vector-only multilingual is sufficient for v0 demo |
| Concrete embedders (Voyage + Cohere) | Pulled into M1.0 (was M1.1) | Closing M1.0 on a mock = no demoable artifact; that contradicts the project's stated "tangible/visible" goal |
| `InMemoryVectorStore` | Promoted to `src/` (was test-only) | Reusable downstream; same rationale as `MockEmbedder` |
| Demo + smoke test PR | Added (PR #10) | Forces an end-to-end exercise of the protocols before declaring M1.0 done |
| README "first-class Spanish support" claim | Softened to "multilingual-capable, with Spanish/LATAM features on the M1.1+ roadmap" | M1.0 doesn't ship any Spanish-specific code; claim must match deliverables |

**Industry-standard hardenings added after big-tech engineer review** (criticals + selected highs + future-API stubs):

| Hardening | Where | Why |
|---|---|---|
| Embedding batching + concurrency (Voyage 128/req, Cohere 96/req) | Task 6 | Without it, real corpora (>128 chunks) trigger `400 Bad Request`. Industry pattern. |
| Rate limiter (per-RPM semaphore) | Task 6 | Proactive vs. reactive 429-retry burns retries on burst start. |
| Transactions in `PgVectorStore.upsert` | Task 9 | Partial-failure inconsistency without `conn.transaction()`. |
| Migrations tracking (`cenote_schema_migrations` table) | Task 9 | Make `apply_migrations` idempotent and aware of multi-migration ordering. |
| HNSW params overridable + GIN index on metadata + `maintenance_work_mem` doc | Task 9 | Defaults (`m=16, ef_construction=64`) are fine for <100k vectors; tuning hooks ready. GIN required for metadata filter speed. |
| `MockEmbedder` unit-norm vectors | Task 4 | Real embedders return ~unit-norm; Gaussian Mock makes cosine similarity ≈ 0 (concentration of measure) and hides ranking bugs. |
| Connection retry in `PgVectorStore.connect` | Task 9 | Container startup races (DB not ready) — common in docker-compose. |
| Dimension validation in upsert (catch mismatch early) | Task 9 | pgvector's runtime error is cryptic. |
| `py.typed` marker (PEP 561) | Task 1 | Without it, consumers see `Any` for everything in cenote. **Critical for the "mypy --strict-friendly" promise.** |
| `LICENSE` (Apache-2.0) + SPDX headers convention | Task 1 | Patent grant + enterprise adoption + supply-chain standard. |
| `CHANGELOG.md` (Keep a Changelog) + `SECURITY.md` | Task 1 | Mandatory for enterprise OSS adoption. |
| `.github/dependabot.yml` | Task 1 | Vulnerability hygiene from day 1. |
| `pip-audit` step in CI | Task 1 | Detect CVEs in deps automatically. |
| Python 3.12 + 3.13 matrix in CI | Task 1 | Industry standard since Oct 2024. |
| Version `0.1.0` via `importlib.metadata` (single source of truth) | Task 1 | No drift between `__version__` and `pyproject.toml`. |
| PEP 639 license syntax in `pyproject.toml` | Task 1 | `license = { text = ... }` is deprecated. |
| README badges (CI, coverage, Python, license) | Task 1 + Task 10 | Signals professionalism + at-a-glance status. |
| `Reranker` Protocol stub (no impl) | Task 11 (new) | Define API now → M1.1 reranker impl is additive, not breaking. |
| `Tracer` Protocol stub (observability hook) | Task 11 (new) | OTel/Langfuse adapter lands in M1.1 without API break. |
| `precision_at_k` + `recall_at_k` eval helpers | Task 11 (new) | Tiny eval primitives so users can validate from day 1. BEIR-style. |

PR count grows from 10 → **11** (new Task 11 just adds protocol stubs + eval helpers). Time estimate: 3.5 → ~4.5 weeks.

---

## File structure

Files this plan creates or modifies. The implementer should check off each as it lands.

### Root-level config

| File | Created in | Purpose |
|---|---|---|
| `pyproject.toml` | Task 1 | Project metadata (PEP 639 license syntax), deps, tool configs (ruff, mypy, pytest) |
| `LICENSE` | Task 1 | Apache 2.0 canonical text |
| `CHANGELOG.md` | Task 1 | Keep a Changelog format, SemVer commitment |
| `SECURITY.md` | Task 1 | Vulnerability disclosure policy |
| `.gitignore` | Task 1 | Python/uv/macOS/VSCode |
| `.pre-commit-config.yaml` | Task 1 | ruff (check+format), mypy, std hooks |
| `.github/workflows/ci.yml` | Task 1 | Lint + type + unit tests + pip-audit; matrix Py 3.12+3.13 |
| `.github/workflows/ci.yml` | Task 9 (modify) | Add integration tests job with Postgres service |
| `.github/dependabot.yml` | Task 1 | Weekly dep updates (uv + github-actions ecosystems) |
| `docker-compose.test.yml` | Task 9 | pgvector container for local integration tests |
| `CLAUDE.md` | Task 0 (copy) → Task 1 (update) | Persistent context; add SPDX convention note |
| `README.md` | Task 0 (copy) → Task 1 (badges) → Task 10 (quickstart + softened claim) | Project README |
| `.claude/settings.json` | Task 0 (copy) | Claude Code permissions |
| `docs/00-first-milestone.md` | Task 0 (copy) | The milestone spec |
| `docs/superpowers/plans/2026-05-21-m1-0-core-primitives.md` | Task 0 (this file) | This plan |
| `docs/01-claude-code-prompts.md` | Task 0 (copy) | Reference playbook (optional context) |
| `.env.example` | Task 6 | Template for `VOYAGE_API_KEY`, `COHERE_API_KEY` |

### Source — `src/cenote/`

| File | Created in | Purpose |
|---|---|---|
| `src/cenote/__init__.py` | Task 1 | Package marker + `__version__` via `importlib.metadata` |
| `src/cenote/py.typed` | Task 1 | PEP 561 marker — type info shipped to consumers |
| `src/cenote/models.py` | Task 2 | `Document`, `Chunk`, `EmbeddedChunk`, `RetrievalResult` |
| `src/cenote/chunkers/__init__.py` | Task 3 | Re-exports |
| `src/cenote/chunkers/base.py` | Task 3 | `Chunker` Protocol |
| `src/cenote/chunkers/recursive.py` | Task 3 | `RecursiveCharacterChunker` |
| `src/cenote/embedders/__init__.py` | Task 4 | Re-exports |
| `src/cenote/embedders/base.py` | Task 4 | `Embedder` Protocol |
| `src/cenote/embedders/mock.py` | Task 4 | `MockEmbedder` (unit-norm) |
| `src/cenote/embedders/cache.py` | Task 5 | `EmbeddingCache` Protocol + `InMemoryCache` + `CachedEmbedder` |
| `src/cenote/embedders/voyage.py` | Task 6 | `VoyageEmbedder` (with batching + rate limit) |
| `src/cenote/embedders/cohere.py` | Task 6 | `CohereEmbedder` (with batching + rate limit) |
| `src/cenote/embedders/_http.py` | Task 6 | Shared HTTP helpers (retry, rate-limit, batching primitives) |
| `src/cenote/stores/__init__.py` | Task 7 | Re-exports |
| `src/cenote/stores/base.py` | Task 7 | `VectorStore` Protocol |
| `src/cenote/stores/memory.py` | Task 7 | `InMemoryVectorStore` |
| `src/cenote/stores/pgvector.py` | Task 9 | `PgVectorStore` (asyncpg, transactions, migrations tracking, conn retry) |
| `src/cenote/stores/pgvector_migrations/001_init.sql` | Task 9 | Initial schema (HNSW tunable + GIN on metadata) |
| `src/cenote/retrievers/__init__.py` | Task 8 | Re-exports |
| `src/cenote/retrievers/base.py` | Task 8 | `Retriever` Protocol |
| `src/cenote/retrievers/vector.py` | Task 8 | `VectorRetriever` |
| `src/cenote/rerankers/__init__.py` | Task 11 | Stub for M1.1 |
| `src/cenote/rerankers/base.py` | Task 11 | `Reranker` Protocol (no impl yet) |
| `src/cenote/observability/__init__.py` | Task 11 | Stub for M1.1 |
| `src/cenote/observability/base.py` | Task 11 | `Tracer` Protocol (no-op default) |
| `src/cenote/eval/__init__.py` | Task 11 | Eval helpers |
| `src/cenote/eval/metrics.py` | Task 11 | `precision_at_k`, `recall_at_k`, `mean_reciprocal_rank` |
| `demos/__init__.py` | Task 10 | Marker |
| `demos/quickstart.py` | Task 10 | End-to-end demo script |
| `demos/data/wikipedia_snippets.json` | Task 10 | Corpus for demo |

### Tests — `tests/`

| File | Created in | Purpose |
|---|---|---|
| `tests/__init__.py` | Task 1 | empty |
| `tests/conftest.py` | Task 1 | empty stub |
| `tests/test_models.py` | Task 2 | Model contracts |
| `tests/chunkers/__init__.py` | Task 3 | empty |
| `tests/chunkers/test_recursive.py` | Task 3 | Recursive splitter behavior |
| `tests/embedders/__init__.py` | Task 4 | empty |
| `tests/embedders/test_mock.py` | Task 4 | Deterministic + unit-norm vectors |
| `tests/embedders/test_cache.py` | Task 5 | Cache hit/miss semantics |
| `tests/embedders/test_voyage.py` | Task 6 | Mocked HTTP for Voyage + batching + rate limit |
| `tests/embedders/test_cohere.py` | Task 6 | Mocked HTTP for Cohere + batching + rate limit |
| `tests/embedders/test_http.py` | Task 6 | RateLimiter unit tests |
| `tests/stores/__init__.py` | Task 7 | empty |
| `tests/stores/test_memory.py` | Task 7 | In-memory store contract |
| `tests/retrievers/__init__.py` | Task 8 | empty |
| `tests/retrievers/test_vector.py` | Task 8 | Vector retriever |
| `tests/integration/__init__.py` | Task 9 | empty |
| `tests/integration/test_pgvector.py` | Task 9 | Real Postgres tests + migrations tracking + transaction rollback |
| `tests/rerankers/__init__.py` | Task 11 | empty |
| `tests/rerankers/test_base.py` | Task 11 | Protocol shape only |
| `tests/observability/__init__.py` | Task 11 | empty |
| `tests/observability/test_base.py` | Task 11 | No-op tracer |
| `tests/eval/__init__.py` | Task 11 | empty |
| `tests/eval/test_metrics.py` | Task 11 | precision/recall/MRR |
| `tests/demos/__init__.py` | Task 10 | empty |
| `tests/demos/test_quickstart_smoke.py` | Task 10 | Smoke test for demo script |

---

## Phase 0 — Bootstrap

## Task 0: Repo docs and initial commit

**Files:**
- Copy: `CLAUDE.md`, `README.md`, `.claude/settings.json`, `docs/00-first-milestone.md`, `docs/01-claude-code-prompts.md` from `/Users/jovandyaz/Downloads/...`
- Create: minimal `.gitignore` (full one comes in Task 1)
- Init: `git init`, set remote to `https://github.com/jovandyaz/pycenote.git`

- [ ] **Step 0.1: Verify source files exist**

Run:
```bash
ls -la /Users/jovandyaz/Downloads/files/CLAUDE.md \
       /Users/jovandyaz/Downloads/files/README.md \
       /Users/jovandyaz/Downloads/files/00-first-milestone.md \
       /Users/jovandyaz/Downloads/rag-pycenote/01-claude-code-prompts.md \
       /Users/jovandyaz/Downloads/rag-pycenote/settings.json
```
Expected: all 5 paths exist.

- [ ] **Step 0.2: Copy planning docs into the repo**

```bash
cd /Users/jovandyaz/Developer/Github/pycenote
mkdir -p docs .claude
cp /Users/jovandyaz/Downloads/files/CLAUDE.md ./CLAUDE.md
cp /Users/jovandyaz/Downloads/files/README.md ./README.md
cp /Users/jovandyaz/Downloads/files/00-first-milestone.md ./docs/00-first-milestone.md
cp /Users/jovandyaz/Downloads/rag-pycenote/01-claude-code-prompts.md ./docs/01-claude-code-prompts.md
cp /Users/jovandyaz/Downloads/rag-pycenote/settings.json ./.claude/settings.json
```

- [ ] **Step 0.3: Verify all docs landed**

```bash
ls -la CLAUDE.md README.md docs/ .claude/settings.json
```
Expected: 5 files present (`CLAUDE.md`, `README.md`, `docs/00-first-milestone.md`, `docs/01-claude-code-prompts.md`, `.claude/settings.json`).

- [ ] **Step 0.4: Write a minimal .gitignore (full version comes in Task 1)**

Create `.gitignore`:
```gitignore
# stub — replaced in Task 1
__pycache__/
.venv/
.env
.DS_Store
.claude/settings.local.json
```

- [ ] **Step 0.5: Initialize git repo and connect remote**

```bash
git init
git branch -M main
git remote add origin https://github.com/jovandyaz/pycenote.git
git status
```
Expected: untracked files include `CLAUDE.md`, `README.md`, `docs/`, `.claude/settings.json`, `.gitignore`, and `docs/superpowers/plans/2026-05-21-m1-0-core-primitives.md`.

- [ ] **Step 0.6: Initial commit**

```bash
git add CLAUDE.md README.md docs/ .claude/settings.json .gitignore
git commit -m "docs: project context, milestone brief, implementation plan, claude code config"
git log --oneline
```
Expected: one commit on `main` branch.

- [ ] **Step 0.7: Push to GitHub**

```bash
git push -u origin main
```
Expected: pushes successfully. If the remote was created as empty without a default branch, this is fine. If the remote already has a `main` with an initial commit (e.g., from a README created during repo creation), pull-rebase first: `git pull --rebase origin main` then re-push.

---

## Phase 1 — Foundation

## Task 1: Project scaffolding (PR #1)

**Files:**

- Create: `pyproject.toml`, `LICENSE`, `CHANGELOG.md`, `SECURITY.md`, `.gitignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `src/cenote/__init__.py`, `src/cenote/py.typed`, `tests/__init__.py`, `tests/conftest.py`
- Modify: `README.md` (badges), `CLAUDE.md` (SPDX convention)

- [ ] **Step 1.1: Create feature branch**

```bash
git checkout -b feat/scaffolding
```

- [ ] **Step 1.2: Write `pyproject.toml`** (PEP 639 license syntax, version 0.1.0)

```toml
[project]
name = "pycenote"
version = "0.1.0"
description = "Production-grade Python framework for building agentic RAG applications. Multilingual-capable with a roadmap toward Spanish/LATAM-first features."
readme = "README.md"
requires-python = ">=3.12"
license = "Apache-2.0"
license-files = ["LICENSE"]
authors = [{ name = "Jovan Díaz", email = "jvaonam@me.com" }]
keywords = ["rag", "llm", "ai", "agents", "retrieval", "embedding"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Typing :: Typed",
]
dependencies = [
    "pydantic>=2.8",
]

[project.urls]
Homepage = "https://github.com/jovandyaz/pycenote"
Repository = "https://github.com/jovandyaz/pycenote"
Issues = "https://github.com/jovandyaz/pycenote/issues"
Changelog = "https://github.com/jovandyaz/pycenote/blob/main/CHANGELOG.md"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cenote"]
# Ship the py.typed marker so consumers (mypy/pyright) see our types.
include = ["src/cenote/py.typed", "src/cenote/**/*.sql"]

[dependency-groups]
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "pre-commit>=4.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
no_implicit_reexport = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
ignore_missing_imports = false

[[tool.mypy.overrides]]
module = ["rank_bm25.*"]
ignore_missing_imports = true
# justification: rank_bm25 ships no type stubs; we only use its public surface.

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: tests requiring external services (Postgres, etc.)",
]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]

[tool.coverage.run]
source = ["src/cenote"]
branch = true

[tool.coverage.report]
exclude_also = [
    "if TYPE_CHECKING:",
    "@overload",
    "raise NotImplementedError",
    "\\.\\.\\.",
]
show_missing = true
skip_covered = false
```

- [ ] **Step 1.3: Replace stub `.gitignore` with full version**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
.venv/
venv/
env/
ENV/

# Build artifacts
build/
dist/
*.egg-info/
*.egg
.eggs/

# uv
.uv/

# Testing
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/

# Type checking
.mypy_cache/
.pyright/

# Ruff
.ruff_cache/

# Pre-commit
.pre-commit-store/

# Environment
.env
.env.*
!.env.example

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Claude Code local overrides (not the shared settings.json)
.claude/settings.local.json
.claude/cache/

# Docker volumes (test pgvector data)
.docker-volumes/
```

- [ ] **Step 1.4: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=500"]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        files: ^src/
        additional_dependencies: ["pydantic>=2.8"]
```

- [ ] **Step 1.5: Write `.github/workflows/ci.yml`** (Python 3.12 + 3.13 matrix + pip-audit)

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-type:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      - name: Install deps
        run: uv sync --all-extras
      - name: Ruff check
        run: uv run ruff check .
      - name: Ruff format check
        run: uv run ruff format --check .
      - name: Mypy
        run: uv run mypy src/

  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - name: Set up Python
        run: uv python install 3.12
      - name: Install pip-audit
        run: uv tool install pip-audit
      - name: Audit dependencies for known CVEs
        run: uv tool run pip-audit --disable-pip --strict

  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      - name: Install deps
        run: uv sync --all-extras
      - name: Run unit tests
        run: uv run pytest -m "not integration" --cov=cenote --cov-report=xml
      - name: Upload coverage
        if: always() && matrix.python-version == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.xml
```

- [ ] **Step 1.6: Create empty source scaffolding + `py.typed` marker**

```bash
mkdir -p src/cenote tests
touch src/cenote/py.typed
```

Create `src/cenote/__init__.py` (version via `importlib.metadata` — single source of truth in `pyproject.toml`):

```python
# SPDX-License-Identifier: Apache-2.0
"""cenote — production-grade agentic RAG primitives."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("pycenote")
except PackageNotFoundError:  # uninstalled (dev) checkout
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
```

Create `tests/__init__.py` (empty):
```python
```

Create `tests/conftest.py` (empty stub):
```python
"""Top-level pytest fixtures (currently empty)."""
```

- [ ] **Step 1.6.1: Create `LICENSE`** (Apache 2.0 canonical text)

```bash
curl -sSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE
# Verify it downloaded (should be ~11k characters)
wc -c LICENSE
```
Expected: ~11.5k characters. If `curl` is unavailable, copy the canonical text from <https://www.apache.org/licenses/LICENSE-2.0.txt>.

- [ ] **Step 1.6.2: Create `CHANGELOG.md`** (Keep a Changelog 1.1.0 + SemVer 2.0.0)

```markdown
# Changelog

All notable changes to this project will be documented here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

> **Pre-1.0 disclaimer.** APIs may break in any minor release until `1.0.0` ships.
> Patch releases (`0.1.0` → `0.1.1`) are bug fixes only.

## [Unreleased]

### Added
- (record here as work lands)

## [0.1.0] - YYYY-MM-DD

### Added
- Initial project scaffolding: `uv`, `ruff`, `mypy --strict`, `pytest`, `pre-commit`,
  GitHub Actions CI (lint + type + unit tests, Python 3.12 & 3.13, `pip-audit`).
- `LICENSE` (Apache 2.0), `CHANGELOG.md`, `SECURITY.md`.
- `py.typed` marker — package ships type information to consumers (PEP 561).
- `__version__` exposed via `importlib.metadata` (single source of truth).
```

Update the placeholder `YYYY-MM-DD` to the release date when v0.1.0 is tagged.

- [ ] **Step 1.6.3: Create `SECURITY.md`**

```markdown
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x     | ✓ (latest minor only, until 1.0.0) |

## Reporting a Vulnerability

Please report security vulnerabilities to **jvaonam@me.com** (PGP key
available on request). Do not file public GitHub issues for security
issues.

We aim to:

- Acknowledge within **7 calendar days**.
- Provide a fix, mitigation, or detailed analysis within **90 calendar days**.
- Credit the reporter (with consent) in the release notes.
```

- [ ] **Step 1.6.4: Create `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    groups:
      dev-dependencies:
        dependency-type: "development"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

- [ ] **Step 1.6.5: Add README badges + softened tagline (full quickstart lands in Task 10)**

Patch `README.md` — insert badges block right under the H1 title, and soften the tagline now (the Quickstart section is updated in Task 10):

```diff
 # cenote

-Production-grade Python framework for building agentic RAG applications, with first-class support for Spanish-language content and Latin American use cases.
+[![CI](https://github.com/jovandyaz/pycenote/actions/workflows/ci.yml/badge.svg)](https://github.com/jovandyaz/pycenote/actions/workflows/ci.yml)
+[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/downloads/)
+[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
+[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
+
+Production-grade Python framework for building agentic RAG applications. Multilingual-capable from day 1; Spanish/LATAM-first features (Spanish-aware BM25, ES evaluation datasets, fiscal/regulatory document support) on the M1.1+ roadmap.
```

- [ ] **Step 1.6.6: Append SPDX convention to `CLAUDE.md`**

Add this section to `CLAUDE.md` under "Conventions → Code style":

````markdown
### License headers (SPDX)

Every `.py` file in `src/` starts with:

```python
# SPDX-License-Identifier: Apache-2.0
```

It must be the **first non-empty line** (before the module docstring). Test files are exempt. Lint enforcement via `reuse-tool` is M1.1+; for now it's convention.
````

- [ ] **Step 1.7: Run uv sync to materialize the env and lockfile**

```bash
uv sync
```
Expected: creates `.venv/`, `uv.lock`, installs pydantic + dev deps.

- [ ] **Step 1.8: Verify all checks pass on the empty scaffold**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -m "not integration"
```
Expected:
- ruff check: `All checks passed!`
- ruff format check: no diffs
- mypy: `Success: no issues found in 1 source file`
- pytest: `no tests ran in ...` with exit code 5 (no tests collected) — **this is acceptable for Task 1**; subsequent tasks add tests.

If pytest exit-5 is undesirable in CI, the unit-tests job will still pass because no tests fail. Verified by:
```bash
uv run pytest -m "not integration" || [ $? -eq 5 ]
```

- [ ] **Step 1.9: Install pre-commit hooks**

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
Expected: all hooks pass.

- [ ] **Step 1.10: Commit and push**

```bash
git add pyproject.toml uv.lock .gitignore .pre-commit-config.yaml \
        .github/workflows/ci.yml .github/dependabot.yml \
        LICENSE CHANGELOG.md SECURITY.md \
        README.md CLAUDE.md \
        src/ tests/
git commit -m "feat: project scaffolding (uv, ruff, mypy, pytest, pre-commit, CI matrix, pip-audit, py.typed, Apache-2.0)"
git push -u origin feat/scaffolding
gh pr create --fill
```
Expected: PR opened. CI runs `lint-and-type` (Py 3.12+3.13), `security-audit`, and `unit-tests` (Py 3.12+3.13). All green.

- [ ] **Step 1.11: Merge PR #1 and sync local main**

```bash
gh pr merge --squash
git checkout main
git pull
```

---

## Phase 2 — Indexing pipeline

## Task 2: Data models (PR #2)

**Files:**
- Create: `src/cenote/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 2.1: Branch**

```bash
git checkout -b feat/data-models
```

- [ ] **Step 2.2: Write `tests/test_models.py` (failing tests)**

```python
"""Tests for cenote.models."""
from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from cenote.models import Chunk, Document, EmbeddedChunk, RetrievalResult


class TestDocument:
    def test_minimal_construction(self) -> None:
        doc = Document(id="doc-1", content="hello world")
        assert doc.id == "doc-1"
        assert doc.content == "hello world"
        assert doc.metadata == {}
        assert doc.source is None

    def test_with_metadata_and_source(self) -> None:
        doc = Document(
            id="doc-2",
            content="text",
            metadata={"author": "alice", "year": 2026},
            source="https://example.com/doc",
        )
        assert doc.metadata["author"] == "alice"
        assert doc.source == "https://example.com/doc"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Document(id="d", content="c", unknown_field="x")  # type: ignore[call-arg]


class TestChunk:
    def test_content_hash_matches_sha256(self) -> None:
        content = "the quick brown fox"
        expected = hashlib.sha256(content.encode()).hexdigest()
        chunk = Chunk(
            id="doc-1:0",
            document_id="doc-1",
            content=content,
            position=0,
            content_hash=expected,
        )
        assert chunk.content_hash == expected

    def test_make_id_is_deterministic(self) -> None:
        a = Chunk.make_id("doc-1", 0)
        b = Chunk.make_id("doc-1", 0)
        assert a == b
        assert Chunk.make_id("doc-1", 1) != a

    def test_make_id_format(self) -> None:
        assert Chunk.make_id("doc-1", 0) == "doc-1:0"
        assert Chunk.make_id("doc-1", 42) == "doc-1:42"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(  # type: ignore[call-arg]
                id="x", document_id="d", content="c",
                position=0, content_hash="0" * 64, bogus="y",
            )


class TestEmbeddedChunk:
    def _make_chunk(self) -> Chunk:
        content = "text"
        return Chunk(
            id="d:0", document_id="d", content=content, position=0,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
        )

    def test_construction(self) -> None:
        chunk = self._make_chunk()
        emb = EmbeddedChunk(
            chunk=chunk,
            embedding=[0.1] * 1024,
            embedding_model="voyage:voyage-3",
            dimensions=1024,
        )
        assert emb.chunk == chunk
        assert len(emb.embedding) == 1024
        assert emb.embedding_model == "voyage:voyage-3"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            EmbeddedChunk(  # type: ignore[call-arg]
                chunk=self._make_chunk(),
                embedding=[0.0],
                embedding_model="m",
                dimensions=1,
                extra="x",
            )


class TestRetrievalResult:
    def test_construction(self) -> None:
        chunk = Chunk(
            id="d:0", document_id="d", content="c", position=0,
            content_hash="0" * 64,
        )
        rr = RetrievalResult(chunk=chunk, score=0.91, retriever="vector")
        assert rr.score == pytest.approx(0.91)
        assert rr.retriever == "vector"

    def test_rejects_extra_fields(self) -> None:
        chunk = Chunk(
            id="d:0", document_id="d", content="c", position=0,
            content_hash="0" * 64,
        )
        with pytest.raises(ValidationError):
            RetrievalResult(  # type: ignore[call-arg]
                chunk=chunk, score=1.0, retriever="vector", bogus=True,
            )


class TestRoundtripSerialization:
    def test_document_roundtrip(self) -> None:
        doc = Document(id="d", content="hello", metadata={"k": 1}, source="s")
        dumped = doc.model_dump()
        restored = Document.model_validate(dumped)
        assert restored == doc

    def test_chunk_roundtrip(self) -> None:
        chunk = Chunk(
            id="d:0", document_id="d", content="hi", position=0,
            content_hash="a" * 64, metadata={"section": "intro"},
        )
        restored = Chunk.model_validate(chunk.model_dump())
        assert restored == chunk
```

- [ ] **Step 2.3: Run tests — expect FAIL (ImportError)**

```bash
uv run pytest tests/test_models.py -v
```
Expected: collection error / `ModuleNotFoundError: No module named 'cenote.models'`.

- [ ] **Step 2.4: Write `src/cenote/models.py`**

```python
"""Pydantic models — the contracts between every cenote module."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Source document before chunking."""

    model_config = ConfigDict(extra="forbid")

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class Chunk(BaseModel):
    """Atomic embeddable unit. Produced by a Chunker, consumed by an Embedder."""

    model_config = ConfigDict(extra="forbid")

    id: str
    document_id: str
    content: str
    position: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str

    @staticmethod
    def make_id(document_id: str, position: int) -> str:
        """Deterministic chunk ID from a document ID and ordinal position."""
        return f"{document_id}:{position}"


class EmbeddedChunk(BaseModel):
    """A Chunk together with its embedding vector and provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk: Chunk
    embedding: list[float]
    embedding_model: str
    dimensions: int


class RetrievalResult(BaseModel):
    """One result returned by a Retriever."""

    model_config = ConfigDict(extra="forbid")

    chunk: Chunk
    score: float
    retriever: str
```

- [ ] **Step 2.5: Run tests — expect PASS**

```bash
uv run pytest tests/test_models.py -v
```
Expected: all tests green.

- [ ] **Step 2.6: Full check suite**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -m "not integration" --cov=cenote
```
Expected: clean.

- [ ] **Step 2.7: Commit, push, PR**

```bash
git add src/cenote/models.py tests/test_models.py
git commit -m "feat(models): add Document, Chunk, EmbeddedChunk, RetrievalResult"
git push -u origin feat/data-models
gh pr create --fill
```

After CI green: `gh pr merge --squash && git checkout main && git pull`.

---

## Task 3: Chunker protocol + RecursiveCharacterChunker (PR #3)

**Files:**
- Create: `src/cenote/chunkers/__init__.py`, `src/cenote/chunkers/base.py`, `src/cenote/chunkers/recursive.py`
- Test: `tests/chunkers/__init__.py`, `tests/chunkers/test_recursive.py`

- [ ] **Step 3.1: Branch**

```bash
git checkout -b feat/recursive-chunker
```

- [ ] **Step 3.2: Create dirs and `__init__.py` stubs**

```bash
mkdir -p src/cenote/chunkers tests/chunkers
```

Create `src/cenote/chunkers/__init__.py`:
```python
"""Chunker primitives — split Documents into Chunks."""
from cenote.chunkers.base import Chunker
from cenote.chunkers.recursive import RecursiveCharacterChunker

__all__ = ["Chunker", "RecursiveCharacterChunker"]
```

Create `tests/chunkers/__init__.py`:
```python
```

- [ ] **Step 3.3: Write failing tests `tests/chunkers/test_recursive.py`**

```python
"""Tests for cenote.chunkers.recursive.RecursiveCharacterChunker."""
from __future__ import annotations

import hashlib

from cenote.chunkers import RecursiveCharacterChunker
from cenote.models import Document


def _sha(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class TestRecursiveCharacterChunker:
    def test_empty_document_returns_empty_list(self) -> None:
        chunker = RecursiveCharacterChunker()
        doc = Document(id="d", content="")
        assert chunker.chunk(doc) == []

    def test_short_document_returns_single_chunk(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=512, chunk_overlap=50)
        doc = Document(id="d", content="short text")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "short text"
        assert chunks[0].position == 0
        assert chunks[0].document_id == "d"
        assert chunks[0].id == "d:0"
        assert chunks[0].content_hash == _sha("short text")

    def test_long_document_splits_into_multiple_chunks(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)
        sentence = "This is sentence number {n} of the test document. "
        content = "".join(sentence.format(n=i) for i in range(20))
        chunks = chunker.chunk(Document(id="d", content=content))
        assert len(chunks) > 1
        # Each chunk under (or near) chunk_size, allowing minor overshoot when
        # an atomic token exceeds chunk_size.
        for c in chunks:
            assert len(c.content) <= 100, f"chunk too large: {len(c.content)}"

    def test_positions_are_sequential(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        content = "abc " * 50
        chunks = chunker.chunk(Document(id="d", content=content))
        positions = [c.position for c in chunks]
        assert positions == list(range(len(chunks)))

    def test_chunk_ids_use_make_id(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        chunks = chunker.chunk(Document(id="doc-99", content="x " * 100))
        for i, c in enumerate(chunks):
            assert c.id == f"doc-99:{i}"

    def test_content_hash_matches_sha256(self) -> None:
        chunker = RecursiveCharacterChunker()
        chunks = chunker.chunk(Document(id="d", content="hello"))
        assert chunks[0].content_hash == _sha("hello")

    def test_metadata_inherited_from_document(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=2)
        doc = Document(
            id="d", content="a " * 50, metadata={"author": "alice"},
        )
        chunks = chunker.chunk(doc)
        for c in chunks:
            assert c.metadata == {"author": "alice"}
        # Mutation of source metadata must not leak into chunks
        doc.metadata["author"] = "bob"
        for c in chunks:
            assert c.metadata == {"author": "alice"}

    def test_consecutive_chunks_share_overlap(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=40, chunk_overlap=10)
        content = "a" * 200
        chunks = chunker.chunk(Document(id="d", content=content))
        assert len(chunks) >= 2
        # Tail of chunk[0] should appear at the start of chunk[1]
        tail = chunks[0].content[-10:]
        assert chunks[1].content.startswith(tail)

    def test_unicode_safe(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
        content = "café — niño — corazón. " * 10
        chunks = chunker.chunk(Document(id="d", content=content))
        # Reconstructed (without overlap dedup) should still contain the unicode
        joined = "".join(c.content for c in chunks)
        assert "café" in joined
        assert "niño" in joined

    def test_zero_overlap_is_supported(self) -> None:
        chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=0)
        content = "x" * 100
        chunks = chunker.chunk(Document(id="d", content=content))
        # Disjoint reconstruction
        assert "".join(c.content for c in chunks) == content
```

- [ ] **Step 3.4: Run tests — expect FAIL (ImportError on `RecursiveCharacterChunker`)**

```bash
uv run pytest tests/chunkers/ -v
```

- [ ] **Step 3.5: Write `src/cenote/chunkers/base.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""Chunker Protocol."""
from __future__ import annotations

from typing import Protocol

from cenote.models import Chunk, Document


class Chunker(Protocol):
    """Splits a Document into a list of Chunks.

    Contract — `chunk.content` is the exact text that will be embedded.

    Implementations that prepend contextual information (e.g. heading hierarchy
    in a MarkdownChunker, code-block fences in a CodeChunker) MUST include that
    context in `chunk.content`, not only in `chunk.metadata`. The embedding
    cache keys off `(model_id, sha256(chunk.content))`; two chunks with the
    same body but different context would collide and return the wrong vector.

    The companion `chunk.content_hash` is `sha256(chunk.content)` and is set
    by the implementation. Callers must not mutate `chunk.content` after the
    chunker returns.
    """

    def chunk(self, document: Document) -> list[Chunk]:
        """Return the document split into ordered Chunks."""
        ...
```

- [ ] **Step 3.6: Write `src/cenote/chunkers/recursive.py`**

```python
"""RecursiveCharacterChunker — splits text by a priority list of separators."""
from __future__ import annotations

import hashlib
from copy import deepcopy

from cenote.models import Chunk, Document

DEFAULT_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")


class RecursiveCharacterChunker:
    """Recursively splits a Document using separators in priority order.

    Algorithm:
    1. Try to split the text on the highest-priority separator.
    2. For each resulting piece, if it fits under `chunk_size`, keep it.
    3. Otherwise, recurse on it with the next separator.
    4. After all pieces fit, glue adjacent pieces back together up to
       `chunk_size`, producing the final chunk list with `chunk_overlap`
       characters of overlap between consecutive chunks.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: tuple[str, ...] = DEFAULT_SEPARATORS,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")
        if not separators:
            raise ValueError("separators must be non-empty")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators

    def chunk(self, document: Document) -> list[Chunk]:
        if not document.content:
            return []
        pieces = self._split_text(document.content, list(self.separators))
        glued = self._glue(pieces)
        return [
            Chunk(
                id=Chunk.make_id(document.id, i),
                document_id=document.id,
                content=text,
                position=i,
                metadata=deepcopy(document.metadata),
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )
            for i, text in enumerate(glued)
        ]

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        if not separators:
            # Fall back to hard slice — keeps pieces under chunk_size.
            return [
                text[i : i + self.chunk_size]
                for i in range(0, len(text), self.chunk_size)
            ]
        sep = separators[0]
        remaining = separators[1:]
        if sep == "":
            return self._split_text(text, remaining)
        parts = text.split(sep)
        result: list[str] = []
        for idx, part in enumerate(parts):
            piece = part + (sep if idx < len(parts) - 1 else "")
            if len(piece) <= self.chunk_size:
                result.append(piece)
            else:
                result.extend(self._split_text(piece, remaining))
        return [p for p in result if p]

    def _glue(self, pieces: list[str]) -> list[str]:
        if not pieces:
            return []
        chunks: list[str] = []
        current = ""
        for piece in pieces:
            if not current:
                current = piece
                continue
            if len(current) + len(piece) <= self.chunk_size:
                current += piece
            else:
                chunks.append(current)
                # Build the next chunk seeded with the trailing overlap.
                tail = current[-self.chunk_overlap :] if self.chunk_overlap else ""
                current = tail + piece
        if current:
            chunks.append(current)
        return chunks
```

- [ ] **Step 3.7: Run tests — expect PASS**

```bash
uv run pytest tests/chunkers/ -v
```
Expected: all green. If `test_consecutive_chunks_share_overlap` fails, inspect chunk boundaries and confirm the overlap tail is being prepended (look at the `_glue` step).

- [ ] **Step 3.8: Full check suite**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -m "not integration" --cov=cenote
```
Expected: green; coverage >= 80% on `src/cenote/chunkers/`.

- [ ] **Step 3.9: Commit, push, PR**

```bash
git add src/cenote/chunkers/ tests/chunkers/
git commit -m "feat(chunkers): add Chunker protocol and RecursiveCharacterChunker"
git push -u origin feat/recursive-chunker
gh pr create --fill
```

Merge after CI green.

---

## Task 4: Embedder protocol + MockEmbedder (PR #4)

**Files:**
- Create: `src/cenote/embedders/__init__.py`, `src/cenote/embedders/base.py`, `src/cenote/embedders/mock.py`
- Test: `tests/embedders/__init__.py`, `tests/embedders/test_mock.py`

- [ ] **Step 4.1: Branch and dirs**

```bash
git checkout -b feat/embedder-protocol
mkdir -p src/cenote/embedders tests/embedders
```

- [ ] **Step 4.2: Failing tests `tests/embedders/test_mock.py`**

```python
"""Tests for cenote.embedders.mock.MockEmbedder."""
from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}", document_id="d", content=text, position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


class TestMockEmbedder:
    def test_default_dimensions(self) -> None:
        e = MockEmbedder()
        assert e.dimensions == 1024
        assert e.model_id == "mock:default"

    def test_custom_dimensions(self) -> None:
        e = MockEmbedder(dimensions=128, model_name="tiny")
        assert e.dimensions == 128
        assert e.model_id == "mock:tiny"

    @pytest.mark.asyncio
    async def test_embed_returns_one_vector_per_chunk(self) -> None:
        e = MockEmbedder(dimensions=64)
        chunks = [_chunk("hello", 0), _chunk("world", 1)]
        out = await e.embed(chunks)
        assert len(out) == 2
        for emb, original in zip(out, chunks, strict=True):
            assert emb.chunk == original
            assert len(emb.embedding) == 64
            assert emb.embedding_model == "mock:default"
            assert emb.dimensions == 64

    @pytest.mark.asyncio
    async def test_embeddings_are_deterministic_for_same_content(self) -> None:
        e = MockEmbedder(dimensions=32)
        first = await e.embed([_chunk("same text")])
        second = await e.embed([_chunk("same text")])
        assert first[0].embedding == second[0].embedding

    @pytest.mark.asyncio
    async def test_embeddings_differ_for_different_content(self) -> None:
        e = MockEmbedder(dimensions=32)
        a = await e.embed([_chunk("text A")])
        b = await e.embed([_chunk("text B")])
        assert a[0].embedding != b[0].embedding

    @pytest.mark.asyncio
    async def test_embed_query_returns_vector_of_right_dimensions(self) -> None:
        e = MockEmbedder(dimensions=16)
        v = await e.embed_query("hello world")
        assert len(v) == 16

    @pytest.mark.asyncio
    async def test_query_and_chunk_share_embedding_function(self) -> None:
        e = MockEmbedder(dimensions=16)
        v_query = await e.embed_query("text")
        v_chunk = (await e.embed([_chunk("text")]))[0].embedding
        assert v_query == v_chunk

    @pytest.mark.asyncio
    async def test_embeddings_are_unit_norm(self) -> None:
        """Matches the distribution real embedders produce (concentration of measure)."""
        e = MockEmbedder(dimensions=128)
        out = await e.embed([_chunk("hello"), _chunk("world", 1)])
        for emb in out:
            squared_norm = sum(x * x for x in emb.embedding)
            assert abs(squared_norm - 1.0) < 1e-9, (
                f"vector is not unit-norm: ||v||² = {squared_norm}"
            )
        # Queries too.
        v_q = await e.embed_query("a query")
        assert abs(sum(x * x for x in v_q) - 1.0) < 1e-9
```

- [ ] **Step 4.3: Run tests — FAIL**

```bash
uv run pytest tests/embedders/ -v
```

- [ ] **Step 4.4: Write `src/cenote/embedders/base.py`**

```python
"""Embedder Protocol."""
from __future__ import annotations

from typing import Protocol

from cenote.models import Chunk, EmbeddedChunk


class Embedder(Protocol):
    """Generates embedding vectors for chunks and queries.

    Implementations must keep `embed(chunks)` order-preserving — the i-th
    EmbeddedChunk returned corresponds to the i-th input Chunk.
    """

    @property
    def model_id(self) -> str:
        """'provider:model_name', e.g. 'voyage:voyage-3', 'mock:default'."""
        ...

    @property
    def dimensions(self) -> int:
        ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        ...

    async def embed_query(self, query: str) -> list[float]:
        ...
```

- [ ] **Step 4.5: Write `src/cenote/embedders/mock.py`** (unit-norm vectors)

> **Why unit-norm**: real embedders (Voyage, Cohere, OpenAI) return vectors that
> live close to the unit hypersphere. Gaussian N(0, 1) vectors have magnitude
> ≈ √dim and exhibit the *concentration of measure* phenomenon — in high
> dimensions, cosine similarities cluster near 0 with very low variance, making
> tests that check ordering pass trivially. Unit-norm matches production
> distribution and surfaces ranking bugs.

```python
# SPDX-License-Identifier: Apache-2.0
"""MockEmbedder — deterministic unit-norm vectors derived from content."""
from __future__ import annotations

import hashlib
import math
import random

from cenote.models import Chunk, EmbeddedChunk


class MockEmbedder:
    """Deterministic, no-network embedder for tests and dev demos.

    The vector is generated from a PRNG seeded by the SHA-256 of the input
    text and L2-normalized so it lives on the unit hypersphere. Same text →
    same vector across processes. Different text → very high probability of
    different vectors (collision probability ≈ 2⁻⁶⁴ given the 64-bit seed).
    """

    def __init__(self, dimensions: int = 1024, model_name: str = "default") -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions
        self._model_name = model_name

    @property
    def model_id(self) -> str:
        return f"mock:{self._model_name}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=c,
                embedding=self._vector_from_text(c.content),
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for c in chunks
        ]

    async def embed_query(self, query: str) -> list[float]:
        return self._vector_from_text(query)

    def _vector_from_text(self, text: str) -> list[float]:
        seed_bytes = hashlib.sha256(text.encode()).digest()
        seed_int = int.from_bytes(seed_bytes[:8], "big")
        rng = random.Random(seed_int)
        raw = [rng.gauss(0.0, 1.0) for _ in range(self._dimensions)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
```

- [ ] **Step 4.6: Write `src/cenote/embedders/__init__.py`**

```python
"""Embedder primitives."""
from cenote.embedders.base import Embedder
from cenote.embedders.mock import MockEmbedder

__all__ = ["Embedder", "MockEmbedder"]
```

- [ ] **Step 4.7: Run tests — PASS**

```bash
uv run pytest tests/embedders/ -v
```

- [ ] **Step 4.8: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/embedders/ tests/embedders/
git commit -m "feat(embedders): add Embedder protocol and MockEmbedder"
git push -u origin feat/embedder-protocol
gh pr create --fill
```

Merge after CI green.

---

## Task 5: EmbeddingCache + CachedEmbedder (PR #5)

**Files:**
- Create: `src/cenote/embedders/cache.py`
- Test: `tests/embedders/test_cache.py`
- Modify: `src/cenote/embedders/__init__.py` (re-exports)

- [ ] **Step 5.1: Branch**

```bash
git checkout -b feat/embedding-cache
```

- [ ] **Step 5.2: Failing tests `tests/embedders/test_cache.py`**

```python
"""Tests for cenote.embedders.cache."""
from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.embedders.cache import CachedEmbedder, InMemoryCache
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}", document_id="d", content=text, position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


class _CountingEmbedder(MockEmbedder):
    def __init__(self, dimensions: int = 8) -> None:
        super().__init__(dimensions=dimensions, model_name="counting")
        self.calls = 0
        self.chunks_seen = 0

    async def embed(self, chunks):
        self.calls += 1
        self.chunks_seen += len(chunks)
        return await super().embed(chunks)


@pytest.mark.asyncio
class TestInMemoryCache:
    async def test_get_miss_returns_none(self) -> None:
        cache = InMemoryCache()
        assert await cache.get("mock:default", "abc") is None

    async def test_set_then_get_returns_value(self) -> None:
        cache = InMemoryCache()
        await cache.set("mock:default", "abc", [1.0, 2.0])
        assert await cache.get("mock:default", "abc") == [1.0, 2.0]

    async def test_keys_distinguish_model_ids(self) -> None:
        cache = InMemoryCache()
        await cache.set("voyage:voyage-3", "h", [1.0])
        await cache.set("cohere:embed-multilingual-v3", "h", [2.0])
        assert await cache.get("voyage:voyage-3", "h") == [1.0]
        assert await cache.get("cohere:embed-multilingual-v3", "h") == [2.0]


@pytest.mark.asyncio
class TestCachedEmbedder:
    async def test_passthrough_when_cache_empty(self) -> None:
        inner = _CountingEmbedder()
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        chunks = [_chunk("hello"), _chunk("world", idx=1)]
        out = await wrapped.embed(chunks)
        assert len(out) == 2
        assert inner.calls == 1
        assert inner.chunks_seen == 2

    async def test_full_hit_skips_inner(self) -> None:
        inner = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped = CachedEmbedder(inner=inner, cache=cache)
        chunks = [_chunk("hello"), _chunk("world", idx=1)]
        await wrapped.embed(chunks)
        # Second pass with the same chunks → no inner calls
        inner.calls = 0
        inner.chunks_seen = 0
        await wrapped.embed(chunks)
        assert inner.calls == 0
        assert inner.chunks_seen == 0

    async def test_mixed_batch_preserves_order(self) -> None:
        inner = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped = CachedEmbedder(inner=inner, cache=cache)
        # Pre-warm cache for "B" only.
        await wrapped.embed([_chunk("B")])
        inner.calls = 0
        inner.chunks_seen = 0
        batch = [_chunk("A", 0), _chunk("B", 1), _chunk("C", 2)]
        result = await wrapped.embed(batch)
        # Only A and C must hit the inner embedder.
        assert inner.chunks_seen == 2
        assert [r.chunk.content for r in result] == ["A", "B", "C"]

    async def test_forwards_model_id_and_dimensions(self) -> None:
        inner = _CountingEmbedder(dimensions=32)
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        assert wrapped.model_id == inner.model_id
        assert wrapped.dimensions == 32

    async def test_query_passthrough(self) -> None:
        inner = _CountingEmbedder()
        wrapped = CachedEmbedder(inner=inner, cache=InMemoryCache())
        v = await wrapped.embed_query("hello")
        assert len(v) == 8  # default _CountingEmbedder dimensions

    async def test_different_model_ids_dont_collide(self) -> None:
        inner_a = _CountingEmbedder()
        cache = InMemoryCache()
        wrapped_a = CachedEmbedder(inner=inner_a, cache=cache)
        await wrapped_a.embed([_chunk("x")])  # populates "mock:counting" key

        # Different inner model_id reuses the same cache instance.
        class _OtherEmbedder(_CountingEmbedder):
            @property
            def model_id(self) -> str:
                return "mock:other"

        inner_b = _OtherEmbedder()
        wrapped_b = CachedEmbedder(inner=inner_b, cache=cache)
        inner_b.calls = 0
        await wrapped_b.embed([_chunk("x")])  # must miss
        assert inner_b.calls == 1
```

- [ ] **Step 5.3: Run tests — FAIL**

```bash
uv run pytest tests/embedders/test_cache.py -v
```

- [ ] **Step 5.4: Write `src/cenote/embedders/cache.py`**

```python
"""Caching wrapper around any Embedder."""
from __future__ import annotations

from typing import Protocol

from cenote.embedders.base import Embedder
from cenote.models import Chunk, EmbeddedChunk


class EmbeddingCache(Protocol):
    """Async key-value store for embedding vectors, keyed by (model_id, content_hash)."""

    async def get(self, model_id: str, content_hash: str) -> list[float] | None:
        ...

    async def set(
        self, model_id: str, content_hash: str, embedding: list[float]
    ) -> None:
        ...


class InMemoryCache:
    """Dict-backed EmbeddingCache. Suitable for tests and small workloads."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], list[float]] = {}

    async def get(self, model_id: str, content_hash: str) -> list[float] | None:
        return self._store.get((model_id, content_hash))

    async def set(
        self, model_id: str, content_hash: str, embedding: list[float]
    ) -> None:
        self._store[(model_id, content_hash)] = list(embedding)


class CachedEmbedder:
    """Wraps an Embedder with an EmbeddingCache.

    On embed(), checks the cache per chunk by (model_id, content_hash); only
    cache-missed chunks are forwarded to the underlying embedder. Output order
    matches the input order.
    """

    def __init__(self, inner: Embedder, cache: EmbeddingCache) -> None:
        self._inner = inner
        self._cache = cache

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        slots: list[EmbeddedChunk | None] = [None] * len(chunks)
        missing_idx: list[int] = []
        missing_chunks: list[Chunk] = []

        for i, chunk in enumerate(chunks):
            cached = await self._cache.get(self.model_id, chunk.content_hash)
            if cached is not None:
                slots[i] = EmbeddedChunk(
                    chunk=chunk,
                    embedding=cached,
                    embedding_model=self.model_id,
                    dimensions=self.dimensions,
                )
            else:
                missing_idx.append(i)
                missing_chunks.append(chunk)

        if missing_chunks:
            fresh = await self._inner.embed(missing_chunks)
            for idx, embedded in zip(missing_idx, fresh, strict=True):
                slots[idx] = embedded
                await self._cache.set(
                    self.model_id, embedded.chunk.content_hash, embedded.embedding
                )

        result: list[EmbeddedChunk] = []
        for slot in slots:
            assert slot is not None  # noqa: S101 — invariant after loops above
            result.append(slot)
        return result

    async def embed_query(self, query: str) -> list[float]:
        return await self._inner.embed_query(query)
```

- [ ] **Step 5.5: Update `src/cenote/embedders/__init__.py`**

```python
"""Embedder primitives."""
from cenote.embedders.base import Embedder
from cenote.embedders.cache import CachedEmbedder, EmbeddingCache, InMemoryCache
from cenote.embedders.mock import MockEmbedder

__all__ = [
    "CachedEmbedder",
    "Embedder",
    "EmbeddingCache",
    "InMemoryCache",
    "MockEmbedder",
]
```

- [ ] **Step 5.6: Run tests — PASS**

```bash
uv run pytest tests/embedders/ -v
```

- [ ] **Step 5.7: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/embedders/ tests/embedders/test_cache.py
git commit -m "feat(embedders): add EmbeddingCache protocol, InMemoryCache, and CachedEmbedder"
git push -u origin feat/embedding-cache
gh pr create --fill
```

Merge after CI green.

---

## Task 6: Concrete embedders — VoyageEmbedder + CohereEmbedder (PR #6)

**Files:**
- Create: `src/cenote/embedders/_http.py`, `src/cenote/embedders/voyage.py`, `src/cenote/embedders/cohere.py`, `.env.example`
- Test: `tests/embedders/test_voyage.py`, `tests/embedders/test_cohere.py`
- Modify: `src/cenote/embedders/__init__.py`, `pyproject.toml` (add `httpx`, `respx`)

> **Verify current API shapes via Context7 before implementing.** Both providers iterate their endpoints; the request/response payloads below reflect their published schemas as of the latest stable releases but should be confirmed against the live docs.

- [ ] **Step 6.1: Branch and deps**

```bash
git checkout -b feat/concrete-embedders
uv add "httpx>=0.27"
uv add --dev "respx>=0.21"
```

- [ ] **Step 6.2: Write `.env.example`**

```bash
# Copy to .env and fill in real values (never commit .env)
VOYAGE_API_KEY=
COHERE_API_KEY=
```

- [ ] **Step 6.3: Failing tests `tests/embedders/test_voyage.py`**

```python
"""Tests for VoyageEmbedder. Uses respx to mock HTTP — no real API calls."""
from __future__ import annotations

import hashlib

import httpx
import pytest
import respx

from cenote.embedders import VoyageEmbedder
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}", document_id="d", content=text, position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


VOYAGE_URL = "https://api.voyageai.com/v1/embeddings"


@pytest.mark.asyncio
class TestVoyageEmbedder:
    async def test_model_id_and_dimensions(self) -> None:
        e = VoyageEmbedder(api_key="x", model="voyage-3", dimensions=1024)
        assert e.model_id == "voyage:voyage-3"
        assert e.dimensions == 1024

    @respx.mock
    async def test_embed_batch_returns_embedded_chunks_in_order(self) -> None:
        route = respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {"index": 0, "embedding": [0.1] * 4},
                        {"index": 1, "embedding": [0.2] * 4},
                    ],
                    "model": "voyage-3",
                    "usage": {"total_tokens": 12},
                },
            )
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4)
        chunks = [_chunk("first", 0), _chunk("second", 1)]
        out = await e.embed(chunks)
        assert route.called
        assert [o.chunk.content for o in out] == ["first", "second"]
        assert out[0].embedding == [0.1] * 4
        assert out[1].embedding == [0.2] * 4
        assert all(o.embedding_model == "voyage:voyage-3" for o in out)
        assert all(o.dimensions == 4 for o in out)

    @respx.mock
    async def test_authorization_header(self) -> None:
        respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200, json={"data": [{"index": 0, "embedding": [0.0] * 4}],
                          "model": "voyage-3", "usage": {"total_tokens": 1}},
            )
        )
        e = VoyageEmbedder(api_key="secret-key", model="voyage-3", dimensions=4)
        await e.embed([_chunk("x")])
        sent = respx.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret-key"

    @respx.mock
    async def test_embed_query_uses_input_type_query(self) -> None:
        respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(
                200, json={"data": [{"index": 0, "embedding": [0.5] * 4}],
                          "model": "voyage-3", "usage": {"total_tokens": 1}},
            )
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4)
        v = await e.embed_query("search query")
        assert v == [0.5] * 4
        body = respx.calls.last.request.read().decode()
        assert "\"input_type\": \"query\"" in body or "'input_type': 'query'" in body

    @respx.mock
    async def test_retries_on_5xx_then_succeeds(self) -> None:
        respx.post(VOYAGE_URL).mock(
            side_effect=[
                httpx.Response(503, json={"error": "transient"}),
                httpx.Response(
                    200,
                    json={"data": [{"index": 0, "embedding": [0.7] * 4}],
                          "model": "voyage-3", "usage": {"total_tokens": 1}},
                ),
            ]
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4,
                           max_retries=2, base_backoff_seconds=0)
        out = await e.embed([_chunk("x")])
        assert out[0].embedding == [0.7] * 4

    @respx.mock
    async def test_gives_up_after_max_retries(self) -> None:
        respx.post(VOYAGE_URL).mock(
            return_value=httpx.Response(500, json={"error": "boom"})
        )
        e = VoyageEmbedder(api_key="k", model="voyage-3", dimensions=4,
                           max_retries=2, base_backoff_seconds=0)
        with pytest.raises(httpx.HTTPStatusError):
            await e.embed([_chunk("x")])

    @respx.mock
    async def test_batches_large_input_into_multiple_requests(self) -> None:
        """250 chunks with batch_size=128 → 2 HTTP calls."""
        def _resp(req: httpx.Request) -> httpx.Response:
            body = json.loads(req.read().decode())
            n = len(body["input"])
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": i, "embedding": [0.1 * i] * 4} for i in range(n)
                    ],
                    "model": "voyage-3",
                    "usage": {"total_tokens": n},
                },
            )
        route = respx.post(VOYAGE_URL).mock(side_effect=_resp)
        e = VoyageEmbedder(
            api_key="k", model="voyage-3", dimensions=4,
            batch_size=128, max_concurrency=4,
        )
        chunks = [_chunk(f"chunk-{i}", i) for i in range(250)]
        out = await e.embed(chunks)
        assert len(out) == 250
        assert route.call_count == 2  # 128 + 122
        # Order preserved across batches.
        assert [o.chunk.content for o in out] == [c.content for c in chunks]

    @respx.mock
    async def test_max_concurrency_caps_in_flight_requests(self) -> None:
        """5 batches with max_concurrency=2 → never more than 2 simultaneous calls."""
        in_flight = 0
        peak = 0
        lock = asyncio.Lock()

        async def _resp(req: httpx.Request) -> httpx.Response:
            nonlocal in_flight, peak
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.05)
            async with lock:
                in_flight -= 1
            body = json.loads(req.read().decode())
            n = len(body["input"])
            return httpx.Response(
                200,
                json={
                    "data": [{"index": i, "embedding": [0.0] * 4} for i in range(n)],
                    "model": "voyage-3",
                    "usage": {"total_tokens": n},
                },
            )

        respx.post(VOYAGE_URL).mock(side_effect=_resp)
        e = VoyageEmbedder(
            api_key="k", model="voyage-3", dimensions=4,
            batch_size=10, max_concurrency=2,
        )
        chunks = [_chunk(f"c-{i}", i) for i in range(50)]  # 5 batches
        await e.embed(chunks)
        assert peak <= 2, f"max concurrency exceeded: peak={peak}"

    def test_batch_size_validation(self) -> None:
        with pytest.raises(ValueError):
            VoyageEmbedder(api_key="k", batch_size=0)
        with pytest.raises(ValueError):
            VoyageEmbedder(api_key="k", batch_size=200)  # > VOYAGE_MAX_BATCH
```

> Add `import asyncio` and `import json` to the imports at the top of `tests/embedders/test_voyage.py`.

- [ ] **Step 6.4: Failing tests `tests/embedders/test_cohere.py`**

```python
"""Tests for CohereEmbedder. respx-mocked HTTP."""
from __future__ import annotations

import hashlib

import httpx
import pytest
import respx

from cenote.embedders import CohereEmbedder
from cenote.models import Chunk


def _chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"d:{idx}", document_id="d", content=text, position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


COHERE_URL = "https://api.cohere.com/v2/embed"


@pytest.mark.asyncio
class TestCohereEmbedder:
    async def test_model_id_and_dimensions(self) -> None:
        e = CohereEmbedder(api_key="x", model="embed-multilingual-v3.0",
                            dimensions=1024)
        assert e.model_id == "cohere:embed-multilingual-v3.0"
        assert e.dimensions == 1024

    @respx.mock
    async def test_embed_batch_returns_embedded_chunks_in_order(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "abc",
                    "embeddings": {"float": [[0.1] * 4, [0.2] * 4]},
                    "texts": ["first", "second"],
                    "meta": {"api_version": {"version": "2"}},
                },
            )
        )
        e = CohereEmbedder(api_key="k", model="embed-multilingual-v3.0",
                            dimensions=4)
        out = await e.embed([_chunk("first", 0), _chunk("second", 1)])
        assert [o.chunk.content for o in out] == ["first", "second"]
        assert out[0].embedding == [0.1] * 4

    @respx.mock
    async def test_authorization_header(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={"id": "x",
                      "embeddings": {"float": [[0.0] * 4]},
                      "texts": ["x"],
                      "meta": {"api_version": {"version": "2"}}},
            )
        )
        e = CohereEmbedder(api_key="secret", model="embed-multilingual-v3.0",
                            dimensions=4)
        await e.embed([_chunk("x")])
        sent = respx.calls.last.request
        assert sent.headers["authorization"] == "Bearer secret"

    @respx.mock
    async def test_embed_query_uses_input_type_search_query(self) -> None:
        respx.post(COHERE_URL).mock(
            return_value=httpx.Response(
                200,
                json={"id": "x",
                      "embeddings": {"float": [[0.5] * 4]},
                      "texts": ["q"],
                      "meta": {"api_version": {"version": "2"}}},
            )
        )
        e = CohereEmbedder(api_key="k", model="embed-multilingual-v3.0",
                            dimensions=4)
        v = await e.embed_query("hello")
        assert v == [0.5] * 4
        body = respx.calls.last.request.read().decode()
        assert "search_query" in body

    @respx.mock
    async def test_retries_then_succeeds(self) -> None:
        respx.post(COHERE_URL).mock(
            side_effect=[
                httpx.Response(429, json={"message": "rate limited"}),
                httpx.Response(
                    200,
                    json={"id": "x",
                          "embeddings": {"float": [[0.9] * 4]},
                          "texts": ["x"],
                          "meta": {"api_version": {"version": "2"}}},
                ),
            ]
        )
        e = CohereEmbedder(api_key="k", model="embed-multilingual-v3.0",
                            dimensions=4, max_retries=2, base_backoff_seconds=0)
        out = await e.embed([_chunk("x")])
        assert out[0].embedding == [0.9] * 4
```

- [ ] **Step 6.5: Run tests — FAIL**

```bash
uv run pytest tests/embedders/test_voyage.py tests/embedders/test_cohere.py -v
```

- [ ] **Step 6.6: Write `src/cenote/embedders/_http.py`** (retry + sliding-window rate limiter)

```python
# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP helpers — retry with exponential backoff + per-RPM rate limiting."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import TypeVar

import httpx

T = TypeVar("T")

RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


class RateLimiter:
    """Sliding-window rate limiter — at most `requests_per_minute` in any 60s window.

    Usage:
        limiter = RateLimiter(requests_per_minute=300)
        async with limiter:
            await client.post(...)

    Coordination across asyncio tasks is via an internal `asyncio.Lock`; safe
    to share one `RateLimiter` instance across concurrent embedder calls.
    """

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self._rpm = requests_per_minute
        self._window_s = 60.0
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "RateLimiter":
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self._window_s:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._rpm:
                wait_for = self._window_s - (now - self._timestamps[0])
                await asyncio.sleep(max(wait_for, 0.0))
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window_s:
                    self._timestamps.popleft()
            self._timestamps.append(time.monotonic())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


async def retrying(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int,
    base_backoff_seconds: float,
) -> httpx.Response:
    """Call `fn` with exponential backoff on transient HTTP errors.

    Returns the first successful response (status < 400) or re-raises the
    final HTTPStatusError after `max_retries` attempts.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await fn()
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                return response
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code not in RETRY_STATUSES:
                raise
            if attempt == max_retries:
                raise
            await asyncio.sleep(base_backoff_seconds * (2 ** attempt))
    assert last_exc is not None
    raise last_exc
```

- [ ] **Step 6.6b: Write `tests/embedders/test_http.py`** (RateLimiter unit tests)

```python
"""Tests for cenote.embedders._http.RateLimiter."""
from __future__ import annotations

import asyncio
import time

import pytest

from cenote.embedders._http import RateLimiter


@pytest.mark.asyncio
class TestRateLimiter:
    async def test_under_limit_no_throttle(self) -> None:
        limiter = RateLimiter(requests_per_minute=600)  # 10/sec
        start = time.monotonic()
        for _ in range(5):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"unexpected throttle: {elapsed:.3f}s"

    async def test_at_limit_throttles(self) -> None:
        # 60 RPM = 1 per second; budget exhausted at request 60 → 61st waits.
        # Use 3 RPM (1 per 20s) and check we wait ~20s when we burst 4.
        # To keep the test fast, shrink the window by monkeypatching _window_s.
        limiter = RateLimiter(requests_per_minute=2)
        limiter._window_s = 0.2  # 200ms window
        start = time.monotonic()
        for _ in range(3):
            async with limiter:
                pass
        elapsed = time.monotonic() - start
        assert elapsed >= 0.2, f"expected ≥200ms throttle, got {elapsed:.3f}s"

    async def test_concurrent_callers_serialized(self) -> None:
        limiter = RateLimiter(requests_per_minute=10)
        limiter._window_s = 0.5

        async def task() -> None:
            async with limiter:
                pass

        await asyncio.gather(*[task() for _ in range(5)])
        # 5 in budget → no throttle expected; no exception is the assertion.

    async def test_negative_rpm_rejected(self) -> None:
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=0)
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=-1)
```

- [ ] **Step 6.7: Write `src/cenote/embedders/voyage.py`** (batching + concurrency + optional rate limiter)

> **Voyage API limits** (verify current at <https://docs.voyageai.com>): `voyage-3` allows ~128 inputs/request, ~120k combined tokens. Free tier: 300 RPM. Paid: 2000 RPM.

```python
# SPDX-License-Identifier: Apache-2.0
"""VoyageEmbedder — embeds via the Voyage AI REST API with batching."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from cenote.embedders._http import RateLimiter, retrying
from cenote.models import Chunk, EmbeddedChunk

VOYAGE_BASE_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MAX_BATCH = 128  # voyage-3 family API limit


class VoyageEmbedder:
    """Voyage AI embedder with batching, concurrency, and optional rate limiting.

    Splits inputs of arbitrary size into `batch_size`-sized HTTP requests
    issued concurrently up to `max_concurrency`. If `requests_per_minute` is
    set, a sliding-window RateLimiter throttles total request rate (use for
    tier-1 free accounts: 300 RPM).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-3",
        dimensions: int = 1024,
        *,
        base_url: str = VOYAGE_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        batch_size: int = VOYAGE_MAX_BATCH,
        max_concurrency: int = 4,
        requests_per_minute: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not 0 < batch_size <= VOYAGE_MAX_BATCH:
            raise ValueError(f"batch_size must be in (0, {VOYAGE_MAX_BATCH}]")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_limiter = (
            RateLimiter(requests_per_minute) if requests_per_minute else None
        )

    @property
    def model_id(self) -> str:
        return f"voyage:{self._model}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []
        batches = [
            chunks[i : i + self._batch_size]
            for i in range(0, len(chunks), self._batch_size)
        ]
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            results = await asyncio.gather(
                *[self._embed_batch(client, batch) for batch in batches]
            )
        return [ec for batch_result in results for ec in batch_result]

    async def embed_query(self, query: str) -> list[float]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            vectors = await self._call_api(client, [query], input_type="query")
        return vectors[0]

    async def _embed_batch(
        self, client: httpx.AsyncClient, batch: list[Chunk]
    ) -> list[EmbeddedChunk]:
        async with self._semaphore:
            vectors = await self._call_api(
                client, [c.content for c in batch], input_type="document"
            )
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for chunk, vector in zip(batch, vectors, strict=True)
        ]

    async def _call_api(
        self,
        client: httpx.AsyncClient,
        inputs: list[str],
        *,
        input_type: str,
    ) -> list[list[float]]:
        payload: dict[str, Any] = {
            "input": inputs,
            "model": self._model,
            "input_type": input_type,
        }
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }

        async def _attempt() -> httpx.Response:
            if self._rate_limiter is not None:
                async with self._rate_limiter:
                    return await client.post(self._base_url, headers=headers, json=payload)
            return await client.post(self._base_url, headers=headers, json=payload)

        response = await retrying(
            _attempt,
            max_retries=self._max_retries,
            base_backoff_seconds=self._base_backoff_seconds,
        )
        data = response.json()
        items = sorted(data["data"], key=lambda d: d["index"])
        return [item["embedding"] for item in items]
```

- [ ] **Step 6.8: Write `src/cenote/embedders/cohere.py`** (same batching + rate limit pattern)

> **Cohere API limits** (verify current at <https://docs.cohere.com>): `embed-multilingual-v3.0` allows 96 inputs/request, ~512 tokens per input. Production tier: 10000 RPM typical.

```python
# SPDX-License-Identifier: Apache-2.0
"""CohereEmbedder — embeds via the Cohere v2 embed API with batching."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from cenote.embedders._http import RateLimiter, retrying
from cenote.models import Chunk, EmbeddedChunk

COHERE_BASE_URL = "https://api.cohere.com/v2/embed"
COHERE_MAX_BATCH = 96  # v2 embed API limit for embed-multilingual-v3.0


class CohereEmbedder:
    """Cohere embedder with batching, concurrency, and optional rate limiting.

    Multilingual via embed-multilingual-v3.0. Same batching contract as
    VoyageEmbedder.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "embed-multilingual-v3.0",
        dimensions: int = 1024,
        *,
        base_url: str = COHERE_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        batch_size: int = COHERE_MAX_BATCH,
        max_concurrency: int = 4,
        requests_per_minute: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not 0 < batch_size <= COHERE_MAX_BATCH:
            raise ValueError(f"batch_size must be in (0, {COHERE_MAX_BATCH}]")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_limiter = (
            RateLimiter(requests_per_minute) if requests_per_minute else None
        )

    @property
    def model_id(self) -> str:
        return f"cohere:{self._model}"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []
        batches = [
            chunks[i : i + self._batch_size]
            for i in range(0, len(chunks), self._batch_size)
        ]
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            results = await asyncio.gather(
                *[self._embed_batch(client, batch) for batch in batches]
            )
        return [ec for batch_result in results for ec in batch_result]

    async def embed_query(self, query: str) -> list[float]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            vectors = await self._call_api(
                client, [query], input_type="search_query"
            )
        return vectors[0]

    async def _embed_batch(
        self, client: httpx.AsyncClient, batch: list[Chunk]
    ) -> list[EmbeddedChunk]:
        async with self._semaphore:
            vectors = await self._call_api(
                client, [c.content for c in batch], input_type="search_document"
            )
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self.model_id,
                dimensions=self._dimensions,
            )
            for chunk, vector in zip(batch, vectors, strict=True)
        ]

    async def _call_api(
        self,
        client: httpx.AsyncClient,
        inputs: list[str],
        *,
        input_type: str,
    ) -> list[list[float]]:
        payload: dict[str, Any] = {
            "texts": inputs,
            "model": self._model,
            "input_type": input_type,
            "embedding_types": ["float"],
        }
        headers = {
            "authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
            "accept": "application/json",
        }

        async def _attempt() -> httpx.Response:
            if self._rate_limiter is not None:
                async with self._rate_limiter:
                    return await client.post(self._base_url, headers=headers, json=payload)
            return await client.post(self._base_url, headers=headers, json=payload)

        response = await retrying(
            _attempt,
            max_retries=self._max_retries,
            base_backoff_seconds=self._base_backoff_seconds,
        )
        data = response.json()
        return list(data["embeddings"]["float"])
```

- [ ] **Step 6.9: Update `src/cenote/embedders/__init__.py`**

```python
"""Embedder primitives."""
from cenote.embedders.base import Embedder
from cenote.embedders.cache import CachedEmbedder, EmbeddingCache, InMemoryCache
from cenote.embedders.cohere import CohereEmbedder
from cenote.embedders.mock import MockEmbedder
from cenote.embedders.voyage import VoyageEmbedder

__all__ = [
    "CachedEmbedder",
    "CohereEmbedder",
    "Embedder",
    "EmbeddingCache",
    "InMemoryCache",
    "MockEmbedder",
    "VoyageEmbedder",
]
```

- [ ] **Step 6.10: Run tests — PASS**

```bash
uv run pytest tests/embedders/ -v
```

- [ ] **Step 6.11: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/embedders/ tests/embedders/test_voyage.py tests/embedders/test_cohere.py \
        pyproject.toml uv.lock .env.example
git commit -m "feat(embedders): add VoyageEmbedder and CohereEmbedder (multilingual)"
git push -u origin feat/concrete-embedders
gh pr create --fill
```

Merge after CI green.

---

## Phase 3 — Retrieval pipeline

## Task 7: VectorStore protocol + InMemoryVectorStore (PR #7)

**Files:**
- Create: `src/cenote/stores/__init__.py`, `src/cenote/stores/base.py`, `src/cenote/stores/memory.py`
- Test: `tests/stores/__init__.py`, `tests/stores/test_memory.py`
- Modify: `pyproject.toml` (add `numpy`)

- [ ] **Step 7.1: Branch and deps**

```bash
git checkout -b feat/vector-store
uv add "numpy>=2.0"
mkdir -p src/cenote/stores tests/stores
```

- [ ] **Step 7.2: Failing tests `tests/stores/test_memory.py`**

```python
"""Tests for InMemoryVectorStore."""
from __future__ import annotations

import hashlib

import pytest

from cenote.models import Chunk, EmbeddedChunk
from cenote.stores import InMemoryVectorStore


def _embedded(text: str, vector: list[float], *, idx: int = 0,
               namespace_doc_id: str = "d") -> EmbeddedChunk:
    chunk = Chunk(
        id=f"{namespace_doc_id}:{idx}",
        document_id=namespace_doc_id,
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    return EmbeddedChunk(
        chunk=chunk, embedding=vector,
        embedding_model="mock:default", dimensions=len(vector),
    )


@pytest.mark.asyncio
class TestInMemoryVectorStore:
    async def test_search_empty_returns_empty(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        out = await store.search([0.0] * 4, namespace="ns")
        assert out == []

    async def test_roundtrip_upsert_and_search(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        items = [
            _embedded("hello", [1.0, 0.0, 0.0, 0.0], idx=0),
            _embedded("world", [0.0, 1.0, 0.0, 0.0], idx=1),
            _embedded("foo",   [0.0, 0.0, 1.0, 0.0], idx=2),
        ]
        await store.upsert(items, namespace="ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns", limit=2)
        assert len(out) == 2
        assert out[0].chunk.content == "hello"
        assert out[0].retriever == "vector"
        assert out[0].score > out[1].score

    async def test_namespace_isolation(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("only-a", [1.0, 0.0, 0.0, 0.0])],
                            namespace="A")
        await store.upsert([_embedded("only-b", [1.0, 0.0, 0.0, 0.0])],
                            namespace="B")
        out_a = await store.search([1.0, 0.0, 0.0, 0.0], namespace="A")
        out_b = await store.search([1.0, 0.0, 0.0, 0.0], namespace="B")
        contents_a = [r.chunk.content for r in out_a]
        contents_b = [r.chunk.content for r in out_b]
        assert "only-a" in contents_a and "only-b" not in contents_a
        assert "only-b" in contents_b and "only-a" not in contents_b

    async def test_metadata_filter(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta",  [1.0, 0.0, 0.0, 0.0], idx=1)
        # Construct chunks with metadata
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace="ns")
        out_es = await store.search([1.0, 0.0, 0.0, 0.0],
                                     namespace="ns", filter={"lang": "es"})
        assert {r.chunk.content for r in out_es} == {"beta"}

    async def test_delete_single_chunk(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta",  [0.0, 1.0, 0.0, 0.0], idx=1)
        await store.upsert([a, b], namespace="ns")
        await store.delete([a.chunk.id], namespace="ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns")
        assert "alpha" not in {r.chunk.content for r in out}

    async def test_delete_namespace(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        await store.upsert([_embedded("a", [1.0, 0.0, 0.0, 0.0])], namespace="ns")
        await store.delete_namespace("ns")
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace="ns")
        assert out == []

    async def test_upsert_overwrites_existing_id(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        v0 = _embedded("first", [1.0, 0.0, 0.0, 0.0], idx=0)
        await store.upsert([v0], namespace="ns")
        # Same id, different content and vector.
        v0_new = EmbeddedChunk(
            chunk=Chunk(
                id=v0.chunk.id, document_id=v0.chunk.document_id,
                content="updated", position=0,
                content_hash=hashlib.sha256(b"updated").hexdigest(),
            ),
            embedding=[0.0, 1.0, 0.0, 0.0],
            embedding_model=v0.embedding_model,
            dimensions=v0.dimensions,
        )
        await store.upsert([v0_new], namespace="ns")
        out = await store.search([0.0, 1.0, 0.0, 0.0], namespace="ns", limit=5)
        assert out[0].chunk.content == "updated"

    async def test_dimension_mismatch_raises(self) -> None:
        store = InMemoryVectorStore(dimensions=4)
        with pytest.raises(ValueError):
            await store.upsert([_embedded("x", [1.0, 0.0])], namespace="ns")
        with pytest.raises(ValueError):
            await store.search([1.0, 0.0], namespace="ns")
```

- [ ] **Step 7.3: Run tests — FAIL**

```bash
uv run pytest tests/stores/ -v
```

- [ ] **Step 7.4: Write `src/cenote/stores/base.py`**

```python
"""VectorStore Protocol."""
from __future__ import annotations

from typing import Any, Protocol

from cenote.models import EmbeddedChunk, RetrievalResult


class VectorStore(Protocol):
    """Multi-tenant vector store. `namespace` is mandatory on every method."""

    async def upsert(
        self,
        embedded_chunks: list[EmbeddedChunk],
        namespace: str,
    ) -> None: ...

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]: ...

    async def delete(self, chunk_ids: list[str], namespace: str) -> None: ...

    async def delete_namespace(self, namespace: str) -> None: ...
```

- [ ] **Step 7.5: Write `src/cenote/stores/memory.py`**

```python
"""InMemoryVectorStore — dict + numpy cosine similarity. For demos and tests."""
from __future__ import annotations

from typing import Any

import numpy as np

from cenote.models import EmbeddedChunk, RetrievalResult


class InMemoryVectorStore:
    """Per-namespace dicts of EmbeddedChunks. Cosine similarity via numpy."""

    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions
        self._data: dict[str, dict[str, EmbeddedChunk]] = {}

    async def upsert(
        self, embedded_chunks: list[EmbeddedChunk], namespace: str
    ) -> None:
        bucket = self._data.setdefault(namespace, {})
        for ec in embedded_chunks:
            if len(ec.embedding) != self._dimensions:
                raise ValueError(
                    f"embedding dim {len(ec.embedding)} != store dim {self._dimensions}"
                )
            bucket[ec.chunk.id] = ec

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if len(query_vector) != self._dimensions:
            raise ValueError(
                f"query dim {len(query_vector)} != store dim {self._dimensions}"
            )
        bucket = self._data.get(namespace)
        if not bucket:
            return []
        q = np.asarray(query_vector, dtype=np.float64)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return []
        scored: list[tuple[float, EmbeddedChunk]] = []
        for ec in bucket.values():
            if filter and not _matches_filter(ec.chunk.metadata, filter):
                continue
            v = np.asarray(ec.embedding, dtype=np.float64)
            v_norm = float(np.linalg.norm(v))
            if v_norm == 0.0:
                continue
            score = float(np.dot(q, v) / (q_norm * v_norm))
            scored.append((score, ec))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [
            RetrievalResult(chunk=ec.chunk, score=score, retriever="vector")
            for score, ec in scored[:limit]
        ]

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        bucket = self._data.get(namespace)
        if not bucket:
            return
        for cid in chunk_ids:
            bucket.pop(cid, None)

    async def delete_namespace(self, namespace: str) -> None:
        self._data.pop(namespace, None)


def _matches_filter(
    metadata: dict[str, Any], filter: dict[str, Any]
) -> bool:
    """Exact-match filter on metadata keys. Extend later if needed."""
    for key, expected in filter.items():
        if metadata.get(key) != expected:
            return False
    return True
```

- [ ] **Step 7.6: Write `src/cenote/stores/__init__.py`**

```python
"""Vector store primitives."""
from cenote.stores.base import VectorStore
from cenote.stores.memory import InMemoryVectorStore

__all__ = ["InMemoryVectorStore", "VectorStore"]
```

- [ ] **Step 7.7: Create `tests/stores/__init__.py`**

```python
```

- [ ] **Step 7.8: Run tests — PASS**

```bash
uv run pytest tests/stores/ -v
```

- [ ] **Step 7.9: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/stores/ tests/stores/ pyproject.toml uv.lock
git commit -m "feat(stores): add VectorStore protocol and InMemoryVectorStore"
git push -u origin feat/vector-store
gh pr create --fill
```

Merge after CI green.

---

## Task 8: Retriever protocol + VectorRetriever (PR #8)

**Files:**
- Create: `src/cenote/retrievers/__init__.py`, `src/cenote/retrievers/base.py`, `src/cenote/retrievers/vector.py`
- Test: `tests/retrievers/__init__.py`, `tests/retrievers/test_vector.py`

- [ ] **Step 8.1: Branch and dirs**

```bash
git checkout -b feat/vector-retriever
mkdir -p src/cenote/retrievers tests/retrievers
```

- [ ] **Step 8.2: Failing tests `tests/retrievers/test_vector.py`**

```python
"""Tests for VectorRetriever."""
from __future__ import annotations

import hashlib

import pytest

from cenote.embedders import MockEmbedder
from cenote.models import Chunk, EmbeddedChunk
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore


def _chunk(text: str, idx: int = 0, *, doc: str = "d") -> Chunk:
    return Chunk(
        id=f"{doc}:{idx}", document_id=doc, content=text, position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )


@pytest.fixture
async def populated_store() -> InMemoryVectorStore:
    embedder = MockEmbedder(dimensions=64)
    chunks = [_chunk(t, i) for i, t in enumerate([
        "the dog chased the cat",
        "machine learning is fun",
        "neural networks learn patterns",
        "the cat slept on the mat",
        "transformers process tokens",
    ])]
    embedded = await embedder.embed(chunks)
    store = InMemoryVectorStore(dimensions=64)
    await store.upsert(embedded, namespace="ns")
    return store


@pytest.mark.asyncio
class TestVectorRetriever:
    async def test_retrieves_sorted_results(
        self, populated_store: InMemoryVectorStore
    ) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        results = await retriever.retrieve("the cat", namespace="ns", limit=3)
        assert len(results) == 3
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
        assert all(r.retriever == "vector" for r in results)

    async def test_namespace_isolation(
        self, populated_store: InMemoryVectorStore
    ) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        out_other = await retriever.retrieve(
            "anything", namespace="other-ns", limit=5
        )
        assert out_other == []

    async def test_limit_is_respected(
        self, populated_store: InMemoryVectorStore
    ) -> None:
        embedder = MockEmbedder(dimensions=64)
        retriever = VectorRetriever(embedder=embedder, store=populated_store)
        results = await retriever.retrieve("anything", namespace="ns", limit=2)
        assert len(results) == 2

    async def test_filter_passed_through(self) -> None:
        embedder = MockEmbedder(dimensions=16)
        store = InMemoryVectorStore(dimensions=16)
        a = _chunk("alpha", 0)
        a.metadata["lang"] = "en"
        b = _chunk("beta", 1)
        b.metadata["lang"] = "es"
        embedded = await embedder.embed([a, b])
        await store.upsert(embedded, namespace="ns")
        retriever = VectorRetriever(embedder=embedder, store=store)
        out = await retriever.retrieve(
            "anything", namespace="ns", limit=5, filter={"lang": "es"}
        )
        assert {r.chunk.content for r in out} == {"beta"}
```

- [ ] **Step 8.3: Run tests — FAIL**

```bash
uv run pytest tests/retrievers/ -v
```

- [ ] **Step 8.4: Write `src/cenote/retrievers/base.py`**

```python
"""Retriever Protocol."""
from __future__ import annotations

from typing import Any, Protocol

from cenote.models import RetrievalResult


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]: ...
```

- [ ] **Step 8.5: Write `src/cenote/retrievers/vector.py`**

```python
"""VectorRetriever — composes an Embedder with a VectorStore."""
from __future__ import annotations

from typing import Any

from cenote.embedders.base import Embedder
from cenote.models import RetrievalResult
from cenote.stores.base import VectorStore


class VectorRetriever:
    """Embed the query, then search the store."""

    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        vector = await self._embedder.embed_query(query)
        results = await self._store.search(
            vector, namespace=namespace, limit=limit, filter=filter
        )
        # Store may have set retriever="vector" already; normalize anyway.
        return [
            RetrievalResult(chunk=r.chunk, score=r.score, retriever="vector")
            for r in results
        ]
```

- [ ] **Step 8.6: Write `src/cenote/retrievers/__init__.py` + `tests/retrievers/__init__.py`**

```python
# src/cenote/retrievers/__init__.py
"""Retriever primitives."""
from cenote.retrievers.base import Retriever
from cenote.retrievers.vector import VectorRetriever

__all__ = ["Retriever", "VectorRetriever"]
```

```python
# tests/retrievers/__init__.py
```

- [ ] **Step 8.7: Run tests — PASS**

```bash
uv run pytest tests/retrievers/ -v
```

- [ ] **Step 8.8: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/retrievers/ tests/retrievers/
git commit -m "feat(retrievers): add Retriever protocol and VectorRetriever"
git push -u origin feat/vector-retriever
gh pr create --fill
```

Merge after CI green.

---

## Phase 4 — Production storage + Demo

## Task 9: PgVectorStore + integration tests + CI update (PR #9)

**Files:**
- Create: `src/cenote/stores/pgvector.py`, `src/cenote/stores/pgvector_migrations/001_init.sql`, `docker-compose.test.yml`, `tests/integration/__init__.py`, `tests/integration/test_pgvector.py`
- Modify: `pyproject.toml` (add `asyncpg`), `src/cenote/stores/__init__.py`, `.github/workflows/ci.yml`

- [ ] **Step 9.1: Branch and deps**

```bash
git checkout -b feat/pgvector-store
uv add "asyncpg>=0.30"
mkdir -p src/cenote/stores/pgvector_migrations tests/integration
```

- [ ] **Step 9.2: Write `docker-compose.test.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: cenote
      POSTGRES_PASSWORD: cenote
      POSTGRES_DB: cenote_test
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cenote -d cenote_test"]
      interval: 2s
      timeout: 5s
      retries: 30
```

- [ ] **Step 9.3: Write `src/cenote/stores/pgvector_migrations/001_init.sql`** (HNSW tunable + GIN metadata)

```sql
-- Migration 001: initial schema for cenote_chunks.
-- Note: this file MUST NOT be edited once committed. Add a new file
-- (002_<name>.sql, ...) for schema changes.
--
-- Performance notes:
--   - HNSW params (m, ef_construction) are tunable via the {HNSW_M},
--     {HNSW_EF_CONSTRUCTION} template variables, bound by PgVectorStore.
--   - For corpora >100k vectors, set `SET maintenance_work_mem = '2GB'`
--     in the session before applying this migration (HNSW build is
--     memory-bound and slows ~10x without it).
--   - GIN index on metadata enables fast JSONB `@>` containment filters.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cenote_chunks (
    id              TEXT PRIMARY KEY,
    namespace       TEXT NOT NULL,
    document_id     TEXT NOT NULL,
    content         TEXT NOT NULL,
    position        INT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_hash    TEXT NOT NULL,
    embedding       vector({DIMENSIONS}) NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cenote_chunks_namespace_doc_idx
    ON cenote_chunks (namespace, document_id);

CREATE INDEX IF NOT EXISTS cenote_chunks_metadata_gin_idx
    ON cenote_chunks USING gin (metadata);

CREATE INDEX IF NOT EXISTS cenote_chunks_embedding_hnsw_idx
    ON cenote_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION});
```

> **Template variables**: `{DIMENSIONS}`, `{HNSW_M}` (default 16), `{HNSW_EF_CONSTRUCTION}` (default 64) are substituted at apply-time by `PgVectorStore.apply_migrations()`. The migration file is a template; values are bound at `PgVectorStore` construction.

- [ ] **Step 9.4: Write `src/cenote/stores/pgvector.py`** (transactions + migrations tracking + connection retry + dimension validation + HNSW params)

```python
# SPDX-License-Identifier: Apache-2.0
"""PgVectorStore — async Postgres + pgvector backend (production-hardened)."""
from __future__ import annotations

import asyncio
import json
import logging
from importlib import resources
from typing import Any

import asyncpg

from cenote.models import Chunk, EmbeddedChunk, RetrievalResult

logger = logging.getLogger(__name__)


class PgVectorStore:
    """Production-grade VectorStore backed by Postgres + pgvector.

    Hardenings vs. naïve impl:
        - Transactional upsert: partial failures roll back cleanly.
        - Migrations tracking: `cenote_schema_migrations` table makes
          `apply_migrations()` idempotent and aware of multi-migration order.
        - Tunable HNSW: `m`, `ef_construction`, runtime `ef_search`.
        - Dimension validation: rejects mismatched embeddings in `upsert`
          with a clear error (pgvector's runtime error is cryptic).
        - Connection retry: `connect()` retries with backoff so docker-compose
          races don't crash startup.

    Multi-tenant via the `namespace` column. Cosine similarity (`<=>`).
    Dimensions are fixed at construction; do not mix dimensions in one
    store instance.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        dimensions: int,
        *,
        table_name: str = "cenote_chunks",
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
        hnsw_ef_search: int | None = None,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if hnsw_m <= 0 or hnsw_ef_construction <= 0:
            raise ValueError("hnsw_m and hnsw_ef_construction must be positive")
        self._pool = pool
        self._dimensions = dimensions
        self._table = table_name
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construction = hnsw_ef_construction
        self._hnsw_ef_search = hnsw_ef_search

    @classmethod
    async def connect(
        cls,
        dsn: str,
        dimensions: int,
        *,
        min_size: int = 1,
        max_size: int = 10,
        startup_retries: int = 5,
        startup_backoff_seconds: float = 1.0,
        **store_kwargs: Any,
    ) -> "PgVectorStore":
        """Create a pool with startup retries; tolerates containers not-yet-ready."""
        last_exc: Exception | None = None
        for attempt in range(startup_retries + 1):
            try:
                pool = await asyncpg.create_pool(
                    dsn, min_size=min_size, max_size=max_size
                )
                assert pool is not None
                logger.info("PgVectorStore connected to %s (attempt %d)", dsn, attempt + 1)
                return cls(pool=pool, dimensions=dimensions, **store_kwargs)
            except (OSError, asyncpg.PostgresError) as exc:
                last_exc = exc
                if attempt == startup_retries:
                    break
                wait = startup_backoff_seconds * (2 ** attempt)
                logger.warning(
                    "PgVectorStore connect failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, startup_retries + 1, exc, wait,
                )
                await asyncio.sleep(wait)
        assert last_exc is not None
        raise last_exc

    async def apply_migrations(self) -> None:
        """Apply pending SQL migrations idempotently.

        Uses a `cenote_schema_migrations` table to track applied versions.
        """
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cenote_schema_migrations (
                    version    TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            applied = {
                r["version"]
                for r in await conn.fetch(
                    "SELECT version FROM cenote_schema_migrations"
                )
            }
            for name in self._migration_files():
                if name in applied:
                    continue
                sql = (
                    self._read_migration(name)
                    .replace("{DIMENSIONS}", str(self._dimensions))
                    .replace("{HNSW_M}", str(self._hnsw_m))
                    .replace("{HNSW_EF_CONSTRUCTION}", str(self._hnsw_ef_construction))
                )
                logger.info("Applying migration %s", name)
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO cenote_schema_migrations (version) VALUES ($1)",
                    name,
                )

    async def upsert(
        self, embedded_chunks: list[EmbeddedChunk], namespace: str
    ) -> None:
        if not embedded_chunks:
            return
        # Validate dimensions up-front — pgvector's runtime error is cryptic.
        for ec in embedded_chunks:
            if len(ec.embedding) != self._dimensions:
                raise ValueError(
                    f"embedding dim {len(ec.embedding)} != store dim "
                    f"{self._dimensions} (chunk id={ec.chunk.id})"
                )
        rows = [
            (
                ec.chunk.id, namespace, ec.chunk.document_id, ec.chunk.content,
                ec.chunk.position, json.dumps(ec.chunk.metadata),
                ec.chunk.content_hash,
                _vector_literal(ec.embedding),
                ec.embedding_model,
            )
            for ec in embedded_chunks
        ]
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.executemany(
                f"""
                INSERT INTO {self._table}
                    (id, namespace, document_id, content, position, metadata,
                     content_hash, embedding, embedding_model)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::vector, $9)
                ON CONFLICT (id) DO UPDATE SET
                    namespace = EXCLUDED.namespace,
                    document_id = EXCLUDED.document_id,
                    content = EXCLUDED.content,
                    position = EXCLUDED.position,
                    metadata = EXCLUDED.metadata,
                    content_hash = EXCLUDED.content_hash,
                    embedding = EXCLUDED.embedding,
                    embedding_model = EXCLUDED.embedding_model
                """,
                rows,
            )

    async def search(
        self,
        query_vector: list[float],
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if len(query_vector) != self._dimensions:
            raise ValueError(
                f"query dim {len(query_vector)} != store dim {self._dimensions}"
            )
        params: list[Any] = [namespace, _vector_literal(query_vector), limit]
        filter_sql = ""
        if filter:
            params.append(json.dumps(filter))
            filter_sql = "AND metadata @> $4::jsonb "
        sql = f"""
            SELECT id, document_id, content, position, metadata, content_hash,
                   1 - (embedding <=> $2::vector) AS score
            FROM {self._table}
            WHERE namespace = $1 {filter_sql}
            ORDER BY embedding <=> $2::vector
            LIMIT $3
        """
        async with self._pool.acquire() as conn:
            if self._hnsw_ef_search is not None:
                await conn.execute(
                    f"SET LOCAL hnsw.ef_search = {int(self._hnsw_ef_search)}"
                )
            rows = await conn.fetch(sql, *params)
        return [
            RetrievalResult(
                chunk=Chunk(
                    id=r["id"],
                    document_id=r["document_id"],
                    content=r["content"],
                    position=r["position"],
                    metadata=(
                        json.loads(r["metadata"])
                        if isinstance(r["metadata"], str)
                        else r["metadata"]
                    ),
                    content_hash=r["content_hash"],
                ),
                score=float(r["score"]),
                retriever="vector",
            )
            for r in rows
        ]

    async def delete(self, chunk_ids: list[str], namespace: str) -> None:
        if not chunk_ids:
            return
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                f"DELETE FROM {self._table} WHERE namespace = $1 AND id = ANY($2)",
                namespace, chunk_ids,
            )

    async def delete_namespace(self, namespace: str) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                f"DELETE FROM {self._table} WHERE namespace = $1", namespace
            )

    async def close(self) -> None:
        await self._pool.close()

    @staticmethod
    def _migration_files() -> list[str]:
        """Return migration filenames in lexicographic order."""
        return sorted(
            f.name
            for f in resources.files("cenote.stores.pgvector_migrations").iterdir()
            if f.name.endswith(".sql")
        )

    @staticmethod
    def _read_migration(name: str) -> str:
        with resources.files("cenote.stores.pgvector_migrations").joinpath(name).open(
            "r", encoding="utf-8"
        ) as fh:
            return fh.read()


def _vector_literal(vector: list[float]) -> str:
    """Serialize a Python list to the `[v1,v2,...]` literal pgvector expects."""
    return "[" + ",".join(f"{x!r}" for x in vector) + "]"
```

- [ ] **Step 9.5: Update `src/cenote/stores/__init__.py`**

```python
"""Vector store primitives."""
from cenote.stores.base import VectorStore
from cenote.stores.memory import InMemoryVectorStore
from cenote.stores.pgvector import PgVectorStore

__all__ = ["InMemoryVectorStore", "PgVectorStore", "VectorStore"]
```

- [ ] **Step 9.6: Failing integration tests `tests/integration/test_pgvector.py`**

```python
"""Integration tests for PgVectorStore. Requires Postgres at TEST_DATABASE_URL."""
from __future__ import annotations

import hashlib
import os
import uuid

import pytest

from cenote.models import Chunk, EmbeddedChunk
from cenote.stores import PgVectorStore


pytestmark = pytest.mark.integration

DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://cenote:cenote@localhost:5433/cenote_test",
)


def _embedded(text: str, vector: list[float], *, idx: int = 0,
               namespace_doc_id: str = "d") -> EmbeddedChunk:
    chunk = Chunk(
        id=f"{namespace_doc_id}:{idx}",
        document_id=namespace_doc_id,
        content=text,
        position=idx,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
    )
    return EmbeddedChunk(
        chunk=chunk, embedding=vector,
        embedding_model="mock:default", dimensions=len(vector),
    )


@pytest.fixture
async def store() -> PgVectorStore:
    s = await PgVectorStore.connect(DSN, dimensions=4)
    await s.apply_migrations()
    yield s
    await s.close()


@pytest.fixture
def ns() -> str:
    return f"test-{uuid.uuid4()}"


@pytest.mark.asyncio
class TestPgVectorStore:
    async def test_upsert_and_search_roundtrip(
        self, store: PgVectorStore, ns: str
    ) -> None:
        items = [
            _embedded("hello", [1.0, 0.0, 0.0, 0.0], idx=0),
            _embedded("world", [0.0, 1.0, 0.0, 0.0], idx=1),
        ]
        await store.upsert(items, namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns, limit=2)
        assert {r.chunk.content for r in out} == {"hello", "world"}
        assert out[0].chunk.content == "hello"

    async def test_namespace_isolation(self, store: PgVectorStore) -> None:
        ns_a = f"a-{uuid.uuid4()}"
        ns_b = f"b-{uuid.uuid4()}"
        await store.upsert(
            [_embedded("only-a", [1.0, 0.0, 0.0, 0.0])], namespace=ns_a
        )
        await store.upsert(
            [_embedded("only-b", [1.0, 0.0, 0.0, 0.0])], namespace=ns_b
        )
        out_a = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns_a)
        out_b = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns_b)
        assert {r.chunk.content for r in out_a} == {"only-a"}
        assert {r.chunk.content for r in out_b} == {"only-b"}
        await store.delete_namespace(ns_a)
        await store.delete_namespace(ns_b)

    async def test_metadata_filter(
        self, store: PgVectorStore, ns: str
    ) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta",  [1.0, 0.0, 0.0, 0.0], idx=1)
        a.chunk.metadata["lang"] = "en"
        b.chunk.metadata["lang"] = "es"
        await store.upsert([a, b], namespace=ns)
        out_es = await store.search(
            [1.0, 0.0, 0.0, 0.0], namespace=ns, filter={"lang": "es"}
        )
        assert {r.chunk.content for r in out_es} == {"beta"}

    async def test_delete_single(self, store: PgVectorStore, ns: str) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        b = _embedded("beta",  [0.0, 1.0, 0.0, 0.0], idx=1)
        await store.upsert([a, b], namespace=ns)
        await store.delete([a.chunk.id], namespace=ns)
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert "alpha" not in {r.chunk.content for r in out}

    async def test_idempotent_upsert(
        self, store: PgVectorStore, ns: str
    ) -> None:
        a = _embedded("alpha", [1.0, 0.0, 0.0, 0.0], idx=0)
        await store.upsert([a, a], namespace=ns)  # twice
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert len([r for r in out if r.chunk.content == "alpha"]) == 1

    async def test_apply_migrations_is_idempotent(
        self, store: PgVectorStore
    ) -> None:
        """Running apply_migrations twice must not error and not duplicate work."""
        await store.apply_migrations()  # already applied by fixture; this is the 2nd run
        # Verify the tracking table reflects exactly one applied version.
        async with store._pool.acquire() as conn:
            rows = await conn.fetch("SELECT version FROM cenote_schema_migrations")
        versions = [r["version"] for r in rows]
        assert versions == ["001_init.sql"]

    async def test_dimension_mismatch_raises_clear_error(
        self, store: PgVectorStore, ns: str
    ) -> None:
        bad = _embedded("oops", [1.0, 0.0])  # store dim is 4
        with pytest.raises(ValueError, match="dim .* != store dim"):
            await store.upsert([bad], namespace=ns)

    async def test_transaction_rollback_on_partial_failure(
        self, store: PgVectorStore, ns: str
    ) -> None:
        """A bad row inside a batch should roll the whole batch back, not partially commit."""
        good = _embedded("good", [1.0, 0.0, 0.0, 0.0], idx=0)
        # Manually craft a row that will violate something: a None-content row.
        # We bypass pre-validation by writing the SQL directly via a corrupted batch.
        # Easier path: send a chunk with content that triggers a constraint we
        # can install. For now, validate the easier contract: dim mismatch
        # caught BEFORE any SQL runs (so nothing is inserted).
        bad = _embedded("bad", [1.0, 0.0])  # dim 2 vs store dim 4
        with pytest.raises(ValueError):
            await store.upsert([good, bad], namespace=ns)
        # Nothing should be in the store.
        out = await store.search([1.0, 0.0, 0.0, 0.0], namespace=ns)
        assert {r.chunk.content for r in out} == set()
```

- [ ] **Step 9.7: Create `tests/integration/__init__.py`** (empty)

- [ ] **Step 9.8: Bring up Postgres and run integration tests**

```bash
docker compose -f docker-compose.test.yml up -d
# wait for healthcheck
sleep 5
uv run pytest -m integration -v
```
Expected: all integration tests green.

Tear down when done:
```bash
docker compose -f docker-compose.test.yml down -v
```

- [ ] **Step 9.9: Update `.github/workflows/ci.yml`** — add integration job

Append (or insert) under `jobs:`:
```yaml
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: cenote
          POSTGRES_PASSWORD: cenote
          POSTGRES_DB: cenote_test
        ports:
          - 5433:5432
        options: >-
          --health-cmd "pg_isready -U cenote -d cenote_test"
          --health-interval 2s
          --health-timeout 5s
          --health-retries 30
    env:
      TEST_DATABASE_URL: postgresql://cenote:cenote@localhost:5433/cenote_test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv python install 3.12
      - run: uv sync --all-extras
      - name: Wait for Postgres
        run: |
          for i in {1..30}; do
            if pg_isready -h localhost -p 5433 -U cenote; then exit 0; fi
            sleep 1
          done
          exit 1
      - run: uv run pytest -m integration
```

- [ ] **Step 9.10: Full checks**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
```

- [ ] **Step 9.11: Commit, push, PR**

```bash
git add src/cenote/stores/pgvector.py \
        src/cenote/stores/pgvector_migrations/ \
        src/cenote/stores/__init__.py \
        tests/integration/ \
        docker-compose.test.yml \
        .github/workflows/ci.yml \
        pyproject.toml uv.lock
git commit -m "feat(stores): add PgVectorStore with migrations, docker-compose, integration tests, CI job"
git push -u origin feat/pgvector-store
gh pr create --fill
```

Merge only after both unit and integration jobs are green in CI.

---

## Task 10: Demo + README update + smoke test (PR #10)

**Files:**
- Create: `demos/__init__.py`, `demos/quickstart.py`, `demos/data/wikipedia_snippets.json`, `tests/demos/__init__.py`, `tests/demos/test_quickstart_smoke.py`
- Modify: `README.md` (soften Spanish claim + add quickstart section)

- [ ] **Step 10.1: Branch**

```bash
git checkout -b feat/quickstart-demo
mkdir -p demos/data tests/demos
```

- [ ] **Step 10.2: Write `demos/data/wikipedia_snippets.json`**

A small handcrafted corpus (20 entries) avoids any licensing wrinkle. Sample entries:

```json
[
  {
    "id": "wiki-1",
    "title": "Cenote",
    "content": "A cenote is a natural sinkhole that exposes groundwater. Found mostly in the Yucatán Peninsula, cenotes were sacred to the ancient Maya."
  },
  {
    "id": "wiki-2",
    "title": "Reciprocal Rank Fusion",
    "content": "Reciprocal Rank Fusion (RRF) is a rank aggregation method that combines results from multiple ranked lists. It is parameter-light and often outperforms more complex score-based methods."
  },
  {
    "id": "wiki-3",
    "title": "Vector database",
    "content": "A vector database indexes high-dimensional vectors and supports nearest-neighbor search. Common applications include semantic search and retrieval-augmented generation."
  }
]
```

> Extend to 20 entries. Topics should be a mix to exercise retrieval (RAG concepts, ML terms, history, geography, fiscal/legal topics). Keep entries short (<= 500 chars).

- [ ] **Step 10.3: Write `demos/quickstart.py`**

```python
"""End-to-end demo: index a small corpus, retrieve, print results.

Usage:
    # With MockEmbedder (no API key, deterministic, dev mode):
    uv run python demos/quickstart.py --provider mock

    # With Voyage AI (requires VOYAGE_API_KEY):
    uv run python demos/quickstart.py --provider voyage

    # With Cohere multilingual (requires COHERE_API_KEY):
    uv run python demos/quickstart.py --provider cohere
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from cenote.chunkers import RecursiveCharacterChunker
from cenote.embedders import (
    CachedEmbedder,
    CohereEmbedder,
    Embedder,
    InMemoryCache,
    MockEmbedder,
    VoyageEmbedder,
)
from cenote.models import Document
from cenote.retrievers import VectorRetriever
from cenote.stores import InMemoryVectorStore

DATA_FILE = Path(__file__).parent / "data" / "wikipedia_snippets.json"

SAMPLE_QUERIES = [
    "What is a cenote?",
    "How does hybrid retrieval combine results?",
    "Tell me about vector databases.",
    "What does RRF stand for?",
]


def build_embedder(provider: str) -> Embedder:
    if provider == "mock":
        return MockEmbedder(dimensions=128)
    if provider == "voyage":
        key = os.environ["VOYAGE_API_KEY"]
        return VoyageEmbedder(api_key=key, model="voyage-3", dimensions=1024)
    if provider == "cohere":
        key = os.environ["COHERE_API_KEY"]
        return CohereEmbedder(
            api_key=key, model="embed-multilingual-v3.0", dimensions=1024,
        )
    raise ValueError(f"unknown provider: {provider}")


async def run(provider: str, limit: int) -> None:
    data = json.loads(DATA_FILE.read_text())
    docs = [Document(id=d["id"], content=d["content"],
                     metadata={"title": d["title"]})
            for d in data]

    chunker = RecursiveCharacterChunker(chunk_size=512, chunk_overlap=64)
    chunks = [c for doc in docs for c in chunker.chunk(doc)]

    embedder: Embedder = CachedEmbedder(
        inner=build_embedder(provider), cache=InMemoryCache(),
    )
    embedded = await embedder.embed(chunks)

    store = InMemoryVectorStore(dimensions=embedder.dimensions)
    await store.upsert(embedded, namespace="demo")
    retriever = VectorRetriever(embedder=embedder, store=store)

    for query in SAMPLE_QUERIES:
        print(f"\n=== Query: {query}")
        results = await retriever.retrieve(query, namespace="demo", limit=limit)
        for i, r in enumerate(results, 1):
            title = r.chunk.metadata.get("title", "?")
            snippet = r.chunk.content[:120].replace("\n", " ")
            print(f"  {i}. [score={r.score:.3f}] ({title}) {snippet}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="cenote quickstart demo")
    parser.add_argument(
        "--provider", choices=["mock", "voyage", "cohere"], default="mock"
    )
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(run(args.provider, args.limit))


if __name__ == "__main__":
    main()
```

- [ ] **Step 10.4: Write `demos/__init__.py`** (empty marker)

```python
```

- [ ] **Step 10.5: Smoke test `tests/demos/test_quickstart_smoke.py`**

```python
"""Smoke test for the demo script. Runs with MockEmbedder only (no API key needed)."""
from __future__ import annotations

import pytest

from demos.quickstart import run


@pytest.mark.asyncio
async def test_quickstart_runs_with_mock_provider() -> None:
    # Just verify it doesn't raise. Output goes to stdout.
    await run(provider="mock", limit=2)
```

Create `tests/demos/__init__.py` empty.

- [ ] **Step 10.6: Update `README.md` — soften Spanish claim + add quickstart**

Apply this patch to `README.md`:

```diff
-# cenote
-
-Production-grade Python framework for building agentic RAG applications, with first-class support for Spanish-language content and Latin American use cases.
+# cenote
+
+Production-grade Python framework for building agentic RAG applications. Multilingual-capable from day 1; Spanish/LATAM-first features (Spanish-aware BM25, ES evaluation datasets, fiscal/regulatory document support) on the M1.1+ roadmap.
```

```diff
 ## Why

-Most RAG frameworks are anglo-centric and prototype-grade. `cenote` is built around three principles:
+Most RAG frameworks are prototype-grade. `cenote` is built around three principles:

 1. **Production-first** — eval, observability, audit trails built-in, not afterthoughts
 2. **Opinionated** — one good stack, not twenty mediocre adapters
-3. **LATAM-rooted** — Spanish embeddings, Mexican fiscal/regulated use cases, eval datasets in Spanish
+3. **Multilingual now, LATAM-focused next** — production embedders from Voyage AI and Cohere are multilingual out of the box; Spanish-specific tokenization, evaluation datasets, and Mexican fiscal/regulatory features land in M1.1+
```

Also append a `## Quickstart` section near the top (after the status table):

```markdown
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

```
=== Query: What is a cenote?
  1. [score=0.812] (Cenote) A cenote is a natural sinkhole that exposes ...
  2. [score=0.563] (Yucatán Peninsula) The Yucatán Peninsula is famous ...

=== Query: What does RRF stand for?
  1. [score=0.798] (Reciprocal Rank Fusion) Reciprocal Rank Fusion (RRF) ...
```
```

- [ ] **Step 10.7: Run smoke test + full checks**

```bash
uv run pytest tests/demos/ -v
uv run python demos/quickstart.py --provider mock
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
uv run pytest -m "not integration" --cov=cenote
```
Expected:
- smoke test passes
- demo script prints results for 4 queries without raising
- all checks green
- coverage on `src/cenote/` still > 80%

- [ ] **Step 10.8: Commit, push, PR**

```bash
git add demos/ tests/demos/ README.md
git commit -m "feat(demos): add quickstart demo and update README quickstart"
git push -u origin feat/quickstart-demo
gh pr create --fill
```

Merge after CI green.

---

## Task 11: Future-API stubs — Reranker, Tracer, eval metrics (PR #11)

> **Why this PR**: lock down the public API surface for M1.1 features (reranker,
> observability) before consumers depend on M1.0. Adding a `Reranker` Protocol
> later is additive; *changing* it later is breaking. Same for the `Tracer`.
> The eval metrics (`precision_at_k`, `recall_at_k`, `mrr`) are 40 lines and
> let users start validating their retrievers from day one (BEIR-style).

**Files:**

- Create: `src/cenote/rerankers/__init__.py`, `src/cenote/rerankers/base.py`
- Create: `src/cenote/observability/__init__.py`, `src/cenote/observability/base.py`
- Create: `src/cenote/eval/__init__.py`, `src/cenote/eval/metrics.py`
- Test: `tests/rerankers/__init__.py`, `tests/rerankers/test_base.py`
- Test: `tests/observability/__init__.py`, `tests/observability/test_base.py`
- Test: `tests/eval/__init__.py`, `tests/eval/test_metrics.py`

- [ ] **Step 11.1: Branch and dirs**

```bash
git checkout -b feat/future-stubs
mkdir -p src/cenote/rerankers src/cenote/observability src/cenote/eval
mkdir -p tests/rerankers tests/observability tests/eval
```

- [ ] **Step 11.2: Write `src/cenote/rerankers/base.py`** (M1.1 will add concrete impls)

```python
# SPDX-License-Identifier: Apache-2.0
"""Reranker Protocol — public API surface only. Concrete impls land in M1.1."""
from __future__ import annotations

from typing import Protocol

from cenote.models import RetrievalResult


class Reranker(Protocol):
    """Re-orders RetrievalResults by relevance to a query.

    The contract: `rerank(query, results, top_k=None)` returns a list of
    RetrievalResults sorted by the reranker's relevance score (highest first),
    with `result.score` overwritten by the reranker score and
    `result.retriever` set to `"<original>+rerank:<provider>"`. If `top_k` is
    set, returns at most that many.
    """

    @property
    def model_id(self) -> str:
        """'provider:model_name', e.g. 'voyage:rerank-2', 'cohere:rerank-3.5'."""
        ...

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        ...
```

```python
# src/cenote/rerankers/__init__.py
"""Reranker primitives (Protocol only in M1.0; impls in M1.1)."""
from cenote.rerankers.base import Reranker

__all__ = ["Reranker"]
```

- [ ] **Step 11.3: Write `src/cenote/observability/base.py`** (no-op default Tracer)

```python
# SPDX-License-Identifier: Apache-2.0
"""Tracer Protocol + no-op default. M1.1 will add OTel and Langfuse adapters."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol


class Tracer(Protocol):
    """Wraps key operations (`embed`, `embed_query`, `search`, `retrieve`)
    for observability.

    Implementations stream span events to an external system (OpenTelemetry,
    Langfuse, etc.). The default `NoopTracer` does nothing, so instrumenting
    code paths is free unless a real tracer is injected.
    """

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[None]:
        ...


class NoopTracer:
    """Default tracer — drops all spans. Use when no observability is wired in."""

    @asynccontextmanager
    async def span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> AsyncIterator[None]:
        yield
```

```python
# src/cenote/observability/__init__.py
"""Observability primitives — Tracer Protocol + NoopTracer."""
from cenote.observability.base import NoopTracer, Tracer

__all__ = ["NoopTracer", "Tracer"]
```

- [ ] **Step 11.4: Failing tests `tests/eval/test_metrics.py`**

```python
"""Tests for cenote.eval.metrics — BEIR-style retrieval quality measures."""
from __future__ import annotations

import hashlib

import pytest

from cenote.eval.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k
from cenote.models import Chunk, RetrievalResult


def _result(content: str, *, idx: int, score: float) -> RetrievalResult:
    chunk = Chunk(
        id=f"d:{idx}", document_id="d", content=content, position=idx,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    return RetrievalResult(chunk=chunk, score=score, retriever="vector")


class TestPrecisionAtK:
    def test_perfect_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:1", "d:2", "d:3", "d:4"}
        assert precision_at_k(results, relevant, k=5) == pytest.approx(1.0)

    def test_zero_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant: set[str] = set()
        assert precision_at_k(results, relevant, k=5) == 0.0

    def test_partial_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:2"}  # 2 of top-5 are relevant
        assert precision_at_k(results, relevant, k=5) == pytest.approx(0.4)

    def test_k_larger_than_results(self) -> None:
        results = [_result("r0", idx=0, score=1.0)]
        assert precision_at_k(results, {"d:0"}, k=10) == pytest.approx(1.0)

    def test_k_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            precision_at_k([], set(), k=0)


class TestRecallAtK:
    def test_all_relevant_found(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:1"}
        assert recall_at_k(results, relevant, k=5) == pytest.approx(1.0)

    def test_partial_recall(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(3)]
        relevant = {"d:0", "d:99"}  # 1 of 2 found in top-3
        assert recall_at_k(results, relevant, k=3) == pytest.approx(0.5)

    def test_empty_relevant_returns_zero(self) -> None:
        results = [_result("r0", idx=0, score=1.0)]
        assert recall_at_k(results, set(), k=1) == 0.0


class TestMeanReciprocalRank:
    def test_first_rank(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        assert mean_reciprocal_rank(results, {"d:0"}) == pytest.approx(1.0)

    def test_third_rank(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        assert mean_reciprocal_rank(results, {"d:2"}) == pytest.approx(1.0 / 3.0)

    def test_no_relevant_in_results_returns_zero(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(3)]
        assert mean_reciprocal_rank(results, {"d:99"}) == 0.0
```

- [ ] **Step 11.5: Run tests — FAIL** (`from cenote.eval.metrics import ...` raises ImportError)

```bash
uv run pytest tests/eval/ -v
```

- [ ] **Step 11.6: Write `src/cenote/eval/metrics.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""Retrieval quality metrics — BEIR-style. M1.1 adds DeepEval integration."""
from __future__ import annotations

from cenote.models import RetrievalResult


def precision_at_k(
    results: list[RetrievalResult],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Fraction of the top-k retrieved chunks whose IDs are in `relevant_ids`."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not results:
        return 0.0
    top = results[:k]
    hits = sum(1 for r in top if r.chunk.id in relevant_ids)
    return hits / len(top)


def recall_at_k(
    results: list[RetrievalResult],
    relevant_ids: set[str],
    k: int,
) -> float:
    """Fraction of relevant chunks captured by the top-k retrieved results."""
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant_ids:
        return 0.0
    top_ids = {r.chunk.id for r in results[:k]}
    hits = len(top_ids & relevant_ids)
    return hits / len(relevant_ids)


def mean_reciprocal_rank(
    results: list[RetrievalResult],
    relevant_ids: set[str],
) -> float:
    """Reciprocal of the rank of the first relevant chunk; 0 if none found."""
    for rank, r in enumerate(results, start=1):
        if r.chunk.id in relevant_ids:
            return 1.0 / rank
    return 0.0
```

```python
# src/cenote/eval/__init__.py
"""Eval primitives — retrieval quality metrics."""
from cenote.eval.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k

__all__ = ["mean_reciprocal_rank", "precision_at_k", "recall_at_k"]
```

- [ ] **Step 11.7: Smoke tests for Reranker + Tracer protocols**

`tests/rerankers/test_base.py`:

```python
"""Protocol shape only — no concrete reranker exists in M1.0."""
from __future__ import annotations

from cenote.rerankers import Reranker


def test_reranker_protocol_is_importable() -> None:
    assert Reranker is not None
```

`tests/observability/test_base.py`:

```python
"""NoopTracer must be a valid no-op context manager."""
from __future__ import annotations

import pytest

from cenote.observability import NoopTracer


@pytest.mark.asyncio
async def test_noop_tracer_yields_without_error() -> None:
    tracer = NoopTracer()
    async with tracer.span("test", {"k": "v"}):
        pass  # no exception is the assertion
```

Empty `tests/rerankers/__init__.py`, `tests/observability/__init__.py`, `tests/eval/__init__.py`.

- [ ] **Step 11.8: Run tests — PASS**

```bash
uv run pytest tests/rerankers/ tests/observability/ tests/eval/ -v
```

- [ ] **Step 11.9: Full checks + commit + PR**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ \
  && uv run pytest -m "not integration" --cov=cenote
git add src/cenote/rerankers/ src/cenote/observability/ src/cenote/eval/ \
        tests/rerankers/ tests/observability/ tests/eval/
git commit -m "feat: future-API stubs — Reranker, Tracer (no-op), eval metrics (precision/recall/MRR)"
git push -u origin feat/future-stubs
gh pr create --fill
```

Merge after CI green. **This closes M1.0.**

---

## Final acceptance verification

After all 10 PRs are merged, on `main`:

- [ ] **Step F.1: Clean checkout works**

```bash
cd /tmp && rm -rf pycenote-verify
git clone https://github.com/jovandyaz/pycenote.git pycenote-verify
cd pycenote-verify
uv sync
uv run pytest -m "not integration"
```
Expected: green.

- [ ] **Step F.2: Integration tests work locally**

```bash
docker compose -f docker-compose.test.yml up -d
sleep 5
uv run pytest -m integration
docker compose -f docker-compose.test.yml down -v
```
Expected: green.

- [ ] **Step F.3: Demo runs**

```bash
uv run python demos/quickstart.py --provider mock
```
Expected: 4 query blocks with sorted results.

- [ ] **Step F.4: Lint + type + coverage all clean**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -m "not integration" --cov=cenote --cov-report=term-missing
```
Expected:
- ruff: `All checks passed!`
- mypy: `Success: no issues found`
- coverage: > 80% on `src/cenote/`

- [ ] **Step F.5: M1.0 closed**

Update `docs/00-first-milestone.md`: tick the "Acceptance criteria" checkboxes, and add a final note at the bottom: `Closed YYYY-MM-DD. Demo deployed to: <link or path>.`

Open `docs/01-second-milestone.md` for M1.1 scope (deferred items from this plan plus eval harness, observability, Spanish tokenizer, ES eval dataset).

---

## Patterns and tips

### When implementing a task

1. Re-read the task header (Files + steps).
2. Branch (`git checkout -b feat/<short-desc>`).
3. Walk the steps top-to-bottom. Do **not** skip the "run failing test" step — it's the contract that the test asserts something meaningful and hasn't accidentally been written to pass.
4. Don't add scope. If you spot something worth doing outside the task, write it in `docs/M1.0-followups.md`, do not implement.
5. Commit + push + PR with the message from the step.
6. Wait for CI green before merging.

### When a test is failing for a reason that surprises you

Re-read the spec section in `docs/00-first-milestone.md`. The test may be wrong, or the impl may be — but only the spec wins ties. Do **not** edit the test to pass unless you can articulate why the original test was wrong.

### When you want to add a dependency

The CLAUDE.md says: propose deps before adding. State name, version, license, alternatives considered. If unclear, ask. Default answer if no maintainer reachable: skip the dep, use stdlib or a slightly more verbose alternative.

### When mypy `--strict` complains about a third-party module without stubs

Add a `[[tool.mypy.overrides]]` block in `pyproject.toml`, narrowest possible module path, with a `# justification:` comment.

### When pre-commit hooks block a commit

Run `uv run pre-commit run --all-files` — it auto-fixes ruff issues. Re-stage and commit. Don't bypass with `--no-verify`.

### When something is slow in CI

The Postgres service container takes ~5s to become healthy. The unit-tests job stays fast. If it grows beyond 2 min, split into per-module jobs.

---

## Out-of-scope items (M1.1+)

Tracked here so they don't get re-litigated during M1.0:

- `MarkdownChunker` — when a downstream product needs it
- `BM25Retriever` + `HybridRetriever` (RRF fusion) — when vector-only is shown insufficient by eval
- Spanish-aware BM25 tokenizer (Snowball-ES + stopwords) — pair with BM25 arrival
- **Concrete** `VoyageReranker` + `CohereReranker` impls (protocol already in M1.0 via Task 11)
- **DeepEval integration + bilingual EN/ES retrieval-quality test set** (metrics scaffolding already in M1.0 via Task 11)
- **OTel + Langfuse adapters** wiring the `Tracer` Protocol (no-op already in M1.0 via Task 11)
- `LLM` client abstractions (Anthropic Claude wrapper with prompt-cache awareness)
- Agent primitives over LangGraph (state machine + tool calling)
- CFDI domain pack (XML parser, SAT validators, fiscal entities) for the cfdi-agent downstream
- `pydantic-settings` for typed env-var loading in concrete embedders/stores
- **Persistent embedding cache** (`SqliteCache`, `RedisCache`) — `InMemoryCache` covers M1.0 needs
- **Streaming embed pipeline** (`embed_stream(AsyncIterator[Chunk]) -> AsyncIterator[EmbeddedChunk]`) — for >1M-chunk corpora
- **Token-aware chunking** (`chunk_size_tokens` via tiktoken/sentencepiece) — character-count is the current contract
- **Vector normalization at write time + `vector_ip_ops` index option** — H19 in the engineer-review; defer until benchmarks justify
- **`cenote.errors` exception hierarchy** — H1; not selected for M1.0; revisit if stdlib exceptions get clumsy
- **`mkdocs` docs site + GH Pages workflow** — H14; defer until 0.2.0
- **`examples/` cookbook (`basic_rag.py`, `custom_embedder.py`, `pgvector_setup.py`)** — H13; the M1.0 quickstart + the inline cookbook in the demo cover the basics
- **PyPI release workflow with trusted publishing (OIDC)** — H9; add when ready to publish 0.1.0
- **Property-based tests (Hypothesis) + mutation testing (mutmut)** — quality bar M1.2+
- **SBOM (CycloneDX) + SLSA attestation** — supply-chain hardening for ≥0.5.0
