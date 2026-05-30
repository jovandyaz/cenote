# ADR-0008 — Monorepo strategy for cenote-core, cenote-agent, cenote-X

**Status**: Proposed
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

cenote-core is shaping up to be the shared foundation for at least three downstream products:

- **cenote-agent** (M2.0+) — agent primitives over LangGraph; the runtime for the LLM-driven layer.
- **knowtis-ai** — RAG + research over the Knowtis notes platform. Currently in a separate repo.
- **cfdi-agent** — accounting reconciliation + CFDI 4.0 compliance for Mexican PYMEs. Currently in a separate repo.

The decision today is **how to organize the code** when cenote-agent comes online, and whether to fold knowtis-ai / cfdi-agent in or keep them separate.

Constraints:
- Single maintainer (Jovan), limited bandwidth.
- cenote-core is on PyPI as `cenote-core`. Breaking API in core forces every downstream to bump.
- `uv` (already in stack) has first-class workspaces support since 2024.

Two patterns dominate the Python world:

1. **Polyrepo** — each package in its own repo. Pros: independent release cadence, smaller blast radius. Cons: cross-repo dep bumping is painful, atomic refactors across packages are hard, tooling (CI, ADRs, conventions) is duplicated.
2. **Monorepo with workspaces** — multiple packages in one repo, each with its own `pyproject.toml`, shared lock file. Used by `polars`, `ruff`, `pydantic`, `pants`, etc. Pros: atomic refactors, shared tooling, one CHANGELOG section per package. Cons: bigger repo, all-or-nothing CI, contributors need to grok the workspace layout.

## Decision (proposed)

Adopt a **`uv` workspace monorepo** for cenote-core + cenote-agent + cenote-integrations-*. Keep knowtis-ai and cfdi-agent **out** of the monorepo (they are products, not framework packages).

### Target layout (when cenote-agent ships)

```
cenote/                           # repo root
├── pyproject.toml                # workspace root: tool config, no package
├── uv.lock                       # shared lockfile
├── packages/
│   ├── cenote-core/              # this current package
│   │   ├── pyproject.toml        # name = "cenote-core"
│   │   └── src/cenote/...
│   ├── cenote-agent/             # M2.0+ — LangGraph runtime
│   │   ├── pyproject.toml        # name = "cenote-agent"
│   │   │                         #   deps: cenote-core = { workspace = true }
│   │   └── src/cenote_agent/...
│   ├── cenote-bench/             # M1.4+ — extracted from cenote.bench when 3+ datasets
│   ├── cenote-cli/               # already seeded by v0.5.0 (cenote bench miracl-es)
│   ├── cenote-rerankers-voyage/  # future — split from core when Reranker impl lands
│   ├── cenote-rerankers-cohere/  # future
│   ├── cenote-llm-openai/        # future — when we add provider beyond Anthropic
│   ├── cenote-llm-bedrock/       # future — AWS Bedrock
│   ├── cenote-llm-vertex/        # future — Google Vertex AI
│   ├── cenote-integrations-pinecone/   # future
│   └── cenote-integrations-qdrant/     # future
├── docs/                         # shared (mkdocs + ADRs)
└── .github/workflows/            # per-package matrix + monorepo-aware
```

### 2026-05-29 — package list expansion

Adopted in v0.5.0 planning conversation: **cenote-bench**, **cenote-rerankers-{voyage,cohere}**, **cenote-llm-{openai,bedrock,vertex}** added to the monorepo target. Rationale per package:

- **cenote-bench**: `cenote.bench` shipped in v0.5.0 (MIRACL-es harness, Pyserini-2cr reporting, CLI). Extract when ≥3 datasets land (BEIR, MTEB-es slice, MIRACL-es). The bench infra has its own dependency footprint (ranx, huggingface_hub, datasets) that doesn't belong in core's runtime path.
- **cenote-rerankers-{voyage,cohere}**: keeps core lean — only the `Reranker` Protocol stays in core; concrete vendor impls split out so consumers don't pull in optional vendor SDKs they don't use.
- **cenote-llm-{openai,bedrock,vertex}**: currently `cenote.llm` ships an Anthropic-only client. When demand for a second provider lands, the pattern is to split per-provider packages (mirrors `langchain-anthropic` / `langchain-openai`) rather than fold them into core.

All seven new packages stay deferred until their use case is real (no speculative scaffolding).

Workspace root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["packages/*"]
```

Each `packages/*/pyproject.toml` declares its own `name`, `version`, `dependencies`. Cross-references use `{ workspace = true }`.

### Migration plan from today's layout

Phase A (no migration needed yet): keep current `src/cenote/` layout while cenote-core matures through M1.3.

Phase B (when cenote-agent design solidifies, ~M2.0 brainstorm): move current `src/cenote/` → `packages/cenote-core/src/cenote/`. One-shot commit, no code changes besides paths. CI matrix and PyPI publishing adjust to per-package workflows.

Phase C (when cenote-agent ships): introduce `packages/cenote-agent/` with its own release cadence on PyPI.

### Versioning & release policy

- Each package versions independently on PyPI (`cenote-core` 0.x, `cenote-agent` 0.x).
- `cenote-agent` declares `cenote-core ~= 0.X` (compatible release) to allow downstream patches.
- Cross-package breaking changes require either (a) a coordinated release of both, or (b) a deprecation period.
- One CHANGELOG.md per package, all in the monorepo.
- One `release-please` config per package (it supports monorepos natively).

### Downstream products stay out

knowtis-ai and cfdi-agent remain in separate repos because:

- They are **products**, not framework packages. They have business logic, web UIs, CI/CD pipelines to staging/prod, different security postures.
- Their release cadence is fundamentally different (continuous deployment vs versioned PyPI).
- Their teams may grow separately from the core maintainer.
- They consume cenote-core as a normal PyPI dep — that boundary keeps them honest about API surface.

## Alternatives considered

**Stay polyrepo.** Each integration in its own repo (e.g., `cenote-pinecone-py`). Rejected because: every new integration duplicates CI/ADRs/conventions; bumping cenote-core API requires N coordinated PRs across N repos; doesn't scale beyond 2-3 packages.

**Single mega-package (`cenote` includes everything).** Rejected: this is what we explicitly avoid in positioning. cenote-core's small surface is a feature.

**Pants or Bazel monorepo.** Overkill for a Python-only project. uv workspaces give us 90% of the value with stdlib-level config.

**`hatchling`'s multi-package mode.** Less mature than uv workspaces; uv is already our dep manager.

**Fold knowtis-ai / cfdi-agent into the monorepo.** Rejected per "downstream products stay out" rationale above. Re-evaluate if a project ever needs atomic cross-cuts.

## Consequences

**Positive**:
- Atomic refactors across cenote-core + cenote-agent become a single PR.
- One source-of-truth for ADRs, CI conventions, mypy config, ruff config.
- Contributors only clone one repo to see the whole framework picture.
- Per-package PyPI versioning preserves downstream flexibility.

**Negative**:
- Phase B migration is a disruptive single commit (paths change). Mitigation: do it during a quiet sprint, document in CHANGELOG.
- CI gets more complex (per-package matrix). Mitigation: GitHub Actions matrix + `uv sync --package <name>` keeps it manageable.
- Newcomers need to learn the workspace layout. Mitigation: explicit README at root pointing to the right package.

**Neutral**:
- knowtis-ai / cfdi-agent depend on cenote-core via PyPI, same as today.
- Pre-Phase B, this ADR has zero immediate impact on the codebase.

## Open questions

1. **CHANGELOG format**: one global, or one per package? Default to per-package.
2. **Mike docs versioning**: one combined site (`/cenote-core/0.4`, `/cenote-agent/0.1`) or two separate sites? Defer; revisit at Phase C.
3. **Per-package integration tests** in CI: how to gate the matrix when only cenote-core changed? `dorny/paths-filter` action handles this; concrete config decided at Phase B.

## References

- [uv workspaces docs](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [polars repo layout](https://github.com/pola-rs/polars) — Rust+Python monorepo reference
- [ruff repo layout](https://github.com/astral-sh/ruff) — multi-crate uv workspace example
- [llama-index repo layout](https://github.com/run-llama/llama_index/tree/main) — Python monorepo reference (Poetry-based; we'll do uv-based)
- ADR-0007 — framework influences (llama-index-core split pattern)
