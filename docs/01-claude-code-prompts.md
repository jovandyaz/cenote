# Claude Code Playbook — `pycenote`

Step-by-step prompts to drive the M1.0 milestone via Claude Code in VSCode. Use these in order. Each prompt is self-contained; copy-paste, let Claude Code work, review, commit, move on.

---

## 0. Setup (before opening Claude Code)

```bash
cd /Users/jovandyaz/Developer/Github/pycenote

# Commit the three context files first
mkdir -p docs .claude
# Drop CLAUDE.md, README.md, docs/00-first-milestone.md, .claude/settings.json from the previous outputs

git add CLAUDE.md README.md docs/00-first-milestone.md .claude/settings.json
git commit -m "docs: project context, milestone brief, claude code config"
git push origin main   # or whichever default branch you chose

# Verify uv is installed
uv --version
# If not: curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then open VSCode at the repo root and start Claude Code. The first thing it should do is read `CLAUDE.md` automatically.

---

## 1. Bootstrap prompt (PR #1 — Scaffolding)

Paste this verbatim as the first message of your session:

> Read `CLAUDE.md` and `docs/00-first-milestone.md` for context. Then implement **PR #1 (Scaffolding)** from the milestone document.
>
> Deliverables:
>
> - `pyproject.toml` using `uv` as the build backend, with project metadata, Python 3.12+ requirement, and dependency groups (`dev` group includes ruff, mypy, pytest, pytest-asyncio, pytest-cov, pre-commit). Runtime deps stay empty for now beyond `pydantic>=2`.
> - `ruff.toml` (or ruff config inside `pyproject.toml`) — strict-ish: line length 100, target-version py312, enable rules `E,W,F,I,N,UP,B,SIM,RUF`, format with double quotes.
> - `mypy.ini` (or in `pyproject.toml`) — strict mode enabled, target Python 3.12, treat missing imports as error except for libraries we know lack stubs.
> - `pytest` config in `pyproject.toml` — testpaths set to `tests`, markers including `integration` registered, asyncio mode `auto`.
> - `.gitignore` — standard Python + uv + VSCode + macOS additions.
> - `.pre-commit-config.yaml` — ruff (check + format), mypy, plus standard hooks (trailing-whitespace, end-of-file-fixer, check-yaml, check-toml).
> - `.github/workflows/ci.yml` — runs on PRs to main: lint, type check, unit tests (no integration tests in this workflow). Uses `astral-sh/setup-uv` action.
> - `src/cenote/__init__.py` exposing `__version__ = "0.0.0"`.
> - `tests/__init__.py` empty, `tests/conftest.py` empty.
>
> Then run `uv sync`, `uv run ruff check .`, `uv run mypy src/`, `uv run pytest`. All should pass cleanly. Stop and show me the output of those four commands.
>
> Do NOT implement any actual library code yet. This PR is scaffolding only.

After it finishes:

```bash
git checkout -b feat/scaffolding
# stage and commit whatever Claude Code generated
git add -A && git commit -m "feat: project scaffolding with uv, ruff, mypy, pytest, pre-commit, ci"
git push -u origin feat/scaffolding
gh pr create --fill   # or open in browser
```

Review the PR yourself before merging. Once merged, move to PR #2.

---

## 2. Data models (PR #2)

> Implement **PR #2 (Data models)** from `docs/00-first-milestone.md`.
>
> Build `src/cenote/models.py` with the Pydantic models exactly as specified in section "1. Data models" of the milestone doc: `Document`, `Chunk`, `EmbeddedChunk`, `RetrievalResult`. Use `model_config = ConfigDict(extra="forbid")` on all of them.
>
> Add a helper `Chunk.make_id(document_id: str, position: int) -> str` that returns a deterministic ID (e.g., `f"{document_id}:{position}"`). Use it inside any code that constructs Chunks.
>
> Add `tests/test_models.py` covering:
>
> - `content_hash` matches `hashlib.sha256(chunk.content.encode()).hexdigest()`
> - `Chunk.make_id` is deterministic and idempotent
> - Models reject extra fields
> - Roundtrip serialization (`model_dump` → `model_validate`) preserves all fields
>
> Run the full check suite (ruff, mypy, pytest) before showing me the diff.

---

## 3. RecursiveCharacterChunker (PR #3)

> Implement **PR #3 (Chunker protocol + RecursiveCharacterChunker)** from `docs/00-first-milestone.md`.
>
> Create:
>
> - `src/cenote/chunkers/__init__.py` re-exporting public types
> - `src/cenote/chunkers/base.py` with the `Chunker` Protocol
> - `src/cenote/chunkers/recursive.py` with `RecursiveCharacterChunker`
> - `tests/chunkers/__init__.py`, `tests/chunkers/test_recursive.py`
>
> Specs are in section "2. Chunker → RecursiveCharacterChunker" of the milestone doc. Default `chunk_size=512`, `chunk_overlap=50`. Separators in priority order: `["\n\n", "\n", ". ", " ", ""]`.
>
> Cover all the test cases listed in the milestone doc plus any edge cases you spot (very long single token, unicode content, mixed whitespace).
>
> Run full checks before showing me the result.

---

## 4. MarkdownChunker (PR #4)

> Implement **PR #4 (MarkdownChunker)** from `docs/00-first-milestone.md`.
>
> Add `src/cenote/chunkers/markdown.py` and `tests/chunkers/test_markdown.py`. Specs in section "2. Chunker → MarkdownChunker".
>
> Reuse `RecursiveCharacterChunker` as the fallback for over-sized sections. Maintain the heading hierarchy in `metadata["headings"]` — a chunk inside `## Subsection` of a doc that starts with `# Title` should have `headings=["Title", "Subsection"]`.
>
> Treat fenced code blocks atomically: never split inside ` ``` ... ``` `. If a code block alone exceeds `chunk_size`, keep it as a single oversized chunk and log a warning.
>
> Full checks pass before showing me the diff.

---

## 5. Embedder protocol + MockEmbedder (PR #5)

> Implement **PR #5 (Embedder protocol + MockEmbedder)** from `docs/00-first-milestone.md`.
>
> Create:
>
> - `src/cenote/embedders/__init__.py`
> - `src/cenote/embedders/base.py` with the `Embedder` Protocol (specs in section "3. Embedder → Protocol")
> - `src/cenote/embedders/mock.py` with `MockEmbedder` (deterministic vectors derived from `chunk.content_hash`, seedable PRNG, configurable dimensions defaulting to 1024)
> - `tests/embedders/test_mock.py`
>
> The MockEmbedder must produce stable vectors across runs: same content_hash → same vector. Embedding the same chunk twice returns identical vectors. Different content → different vectors with high probability.
>
> Full checks pass.

---

## 6. EmbeddingCache + CachedEmbedder (PR #6)

> Implement **PR #6 (EmbeddingCache + InMemoryCache + CachedEmbedder)** from `docs/00-first-milestone.md`.
>
> Specs in section "3. Embedder → Cache protocol / Caching wrapper". Implement:
>
> - `EmbeddingCache` Protocol
> - `InMemoryCache` (dict-backed, async API for protocol consistency)
> - `CachedEmbedder` (wraps any `Embedder`, uses any `EmbeddingCache`)
> - Tests covering: hit avoids underlying call, miss invokes and stores, mixed batch preserves order, different `model_id` produces different cache keys
>
> Use a call-counter mock embedder in tests to assert the underlying embedder is or isn't called.
>
> Full checks pass.

---

## 7. PgVectorStore + integration tests (PR #7)

> Implement **PR #7 (VectorStore protocol + PgVectorStore + integration tests)** from `docs/00-first-milestone.md`.
>
> Specs in section "4. VectorStore". Deliverables:
>
> - `src/cenote/stores/__init__.py`
> - `src/cenote/stores/base.py` with `VectorStore` Protocol
> - `src/cenote/stores/pgvector.py` with `PgVectorStore` using `asyncpg`
> - `src/cenote/stores/pgvector_migrations/001_init.sql`
> - Helper `apply_migrations(conn)` in `pgvector.py`
> - `docker-compose.test.yml` at repo root using image `pgvector/pgvector:pg16`
> - `tests/integration/__init__.py`, `tests/integration/test_pgvector.py` marked `@pytest.mark.integration`
> - Update `.github/workflows/ci.yml` to add a separate job for integration tests (only on PRs to `main`)
>
> Dimensions are a constructor parameter; the table schema uses `vector(N)` where N is configured at instance creation. Cosine similarity by default.
>
> Multi-tenant isolation must be enforced: every query filters by `namespace`. Test that data in namespace A is never returned when querying namespace B.
>
> Before showing me the diff, verify locally:
>
> ```
> docker compose -f docker-compose.test.yml up -d
> uv run pytest -m integration
> docker compose -f docker-compose.test.yml down
> ```

---

## 8. VectorRetriever (PR #8)

> Implement **PR #8 (VectorRetriever)** from `docs/00-first-milestone.md`.
>
> Build `src/cenote/retrievers/__init__.py`, `src/cenote/retrievers/base.py` (Retriever Protocol), `src/cenote/retrievers/vector.py`, and `tests/retrievers/test_vector.py`.
>
> Use `MockEmbedder` + a real `PgVectorStore` (in integration tests) and `MockEmbedder` + an in-memory fake store (in unit tests). Write a tiny `InMemoryVectorStore` in `tests/retrievers/conftest.py` for unit testing (do NOT add it to `src/cenote/` — it's a test fixture only).
>
> Full checks + integration tests pass.

---

## 9. BM25Retriever (PR #9)

> Implement **PR #9 (BM25Retriever)** from `docs/00-first-milestone.md`.
>
> Add `rank_bm25` as a runtime dependency. Build `src/cenote/retrievers/bm25.py` with the per-namespace in-memory index. Provide two constructors: one that loads chunks from a `VectorStore` lazily (production), one that accepts pre-loaded chunks (testing).
>
> Tokenizer: lowercase + simple whitespace split for now. Note in a code comment that a Spanish-aware tokenizer is M1.1 work.
>
> Add `tests/retrievers/test_bm25.py`. Full checks pass.

---

## 10. HybridRetriever (PR #10)

> Implement **PR #10 (HybridRetriever)** from `docs/00-first-milestone.md`.
>
> Build `src/cenote/retrievers/hybrid.py` with RRF fusion (`k=60` default), configurable weights per retriever (default 1.0 each). Returns deduplicated, score-fused results with `retriever="hybrid"`.
>
> Tests in `tests/retrievers/test_hybrid.py`: chunk only in vector results still appears in output; ranking changes when weights change; namespace isolation preserved; empty corpus returns empty list.
>
> Full checks pass. This closes M1.0.

After PR #10 merges, M1.0 is done. Open a new milestone doc for M1.1.

---

## General patterns and tips

### When Claude Code gets stuck on a test

> The test `test_X` is failing. Show me the failure output, then propose the smallest possible fix. Do not change the test unless the test itself is wrong — first verify the implementation matches the milestone spec.

### When you want a smaller scope mid-PR

> Pause. Show me the current diff. We'll commit what's working as a partial PR and finish the rest separately.

### When refactoring across files

> Before making this change, list every file that will need to be touched and why. Then proceed only after I confirm.

### When dependencies are unclear

> Don't add new top-level dependencies without asking. If you think one is needed, propose it with: name, version, license, what alternatives you considered, and what tradeoff you're making.

### To verify everything before declaring done

> Run, in order: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/`, `uv run pytest --cov=cenote -m "not integration"`. Show the full output of each. Only declare done if all four are green and coverage is above 80%.

### To audit progress

> Read `docs/00-first-milestone.md` and tell me which PRs are complete (look at git log), which is in progress, and what's next. Don't change any files.

### When you want Claude Code to take initiative

> Plan the next PR (#N) end-to-end. List the files you'll create or modify, the test cases you'll cover, and any open questions. Wait for my approval before writing code.

---

## Troubleshooting

**`uv sync` fails on a fresh checkout.** Make sure `uv` is at version 0.5+ (`uv self update`). The lockfile is committed; never delete it without intent.

**Pre-commit complains about files Claude Code generated.** Run `uv run pre-commit run --all-files` and let it auto-fix what it can. Re-stage and commit again.

**`mypy --strict` fails on a third-party import without stubs.** Check `pyproject.toml` for `[[tool.mypy.overrides]]` — add an entry with `ignore_missing_imports = true` for the offending module only, with a `# justification: <reason>` comment in the section.

**Integration tests hang on CI.** The Postgres container probably wasn't ready when tests started. Add a healthcheck retry loop in the CI workflow before running `pytest -m integration`.

**Claude Code suggests pulling in LangChain.** Reject it. See `CLAUDE.md` → "What to NOT do".

---

## After M1.0

Open `docs/01-second-milestone.md` and draft M1.1 scope: first concrete embedder (Voyage vs Cohere decision), Reranker protocol, eval harness skeleton, Langfuse hooks. Reuse this playbook's format for the new prompts.
