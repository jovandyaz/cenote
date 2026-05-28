# ADR-0004 — Documentation strategy: mkdocs + mike + ADRs

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

Today (v0.3.0) we have:
- `mkdocs` with `mkdocs-material` theme, served at <https://jovandyaz.github.io/cenote/>
- `mkdocstrings-python` for API doc generation from docstrings
- Single version (latest from main) — no version-pinned URLs
- `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` at repo root
- No ADRs (until now — see ADR-0001 onwards)
- No "When NOT to use cenote" guidance
- No quantified Definition of Done per milestone

Gaps:
- A user on `v0.3.0` reading `https://jovandyaz.github.io/cenote/quickstart/` sees content drafted for `v0.4.0`. This will burn first-time users at the next breaking change.
- Decisions like "why Protocols over ABCs" or "why pgvector over Qdrant" live in commits, chat, or implicit code patterns. Not citable.
- "Production-grade" is asserted, not measured. There is no DoD that a release must hit.

## Decision

Documentation lives in **four layers**, each with a clear audience and lifecycle:

### Layer 1 — User docs (mkdocs site, versioned)

`docs/site/` rendered via `mkdocs` and served at `https://jovandyaz.github.io/cenote/<version>/`.

- **Version with `mike`**. Each release publishes its own URL. `latest` aliases the highest non-pre-release.
- **Audience**: users (devs integrating cenote into their products).
- **Sections**: quickstart, architecture, API reference, extending, benchmarks, FAQ, **"When NOT to use cenote"** (new).

### Layer 2 — ADRs (`docs/adrs/`)

This directory. Architecture decisions, append-only, citable.

- **Audience**: contributors and future-maintainers (including future-Claude).
- **Lifecycle**: see [docs/adrs/README.md](README.md).

### Layer 3 — Operational docs (repo root)

`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `CLAUDE.md`.

- **Audience**: anyone landing on the GitHub repo.
- **Updates**: every release for CHANGELOG; on convention change for the others.

### Layer 4 — Internal planning (`docs/superpowers/`, gitignored)

`STATE.md`, `specs/`, `plans/`. Ephemeral, drives the subagent-driven workflow.

- **Audience**: future-Claude sessions and the maintainer.
- **Lifecycle**: regenerated/superseded as work progresses.

### Cross-cutting commitments

**"When NOT to use cenote"** added to README:
- If you need 100+ integrations out-of-the-box → LangChain/LlamaIndex.
- If you need a hosted RAG service → Vectara, Pinecone Assistants, etc.
- If you need a SaaS chatbot UI → cenote is a library, not an app.
- If your data is < 10k chunks and you don't care about multi-tenancy → SQLite + simple cosine math is enough.

**Definition of Done (per milestone)** documented in [docs/site/dod.md](../site/dod.md) (new). Each milestone must hit:
- Test coverage ≥ 80% (raised per-milestone as repo matures).
- All new public APIs have docstrings rendered by mkdocstrings.
- CHANGELOG entry follows Keep-a-Changelog format with concrete impact statement.
- `mypy --strict` clean, `ruff check .` clean, no new dependency without ADR.
- Benchmarks for any new performance-claimed feature (e.g., "WAL gives 10x" must have a benchmark).
- Migration guide if the release is breaking (pre-1.0 still requires this).

## Alternatives considered

**Sphinx instead of mkdocs.** Sphinx is more powerful but heavier. `mkdocs-material` is more modern, faster to render, and aligned with `pydantic`, `httpx`, `FastAPI` ecosystem.

**ADRs in a separate repo (e.g., `cenote-adrs`).** Rejected. ADRs must be co-located with the code they affect; otherwise they get out of sync.

**ADRs in the GitHub wiki.** Rejected — wiki is not part of the repo's git history, can't be cross-linked from PRs naturally.

**Docs versioning via `mkdocs-versioning`.** Rejected — less maintained than `mike`, which is used by `pydantic`, `mkdocs-material` itself.

## Consequences

**Positive**:
- Users on `v0.3.0` will read v0.3.0 docs, not v0.4.0 docs.
- ADRs make architectural decisions durable and citable from PRs / code reviews.
- DoD turns "production-grade" from marketing into a checklist.

**Negative**:
- `mike` adds publish-step complexity (separate `gh-pages` branch per version). Mitigation: GitHub Action handles it; user never touches.
- ADRs require discipline to write. Mitigation: only for decisions matching the ADR criteria in [README.md](README.md).
- DoD criteria can become bureaucracy if mechanically applied. Mitigation: criteria are guidelines; explicit waiver in CHANGELOG when skipped.

**Neutral**:
- Old docs versions stay on `gh-pages` forever (cheap, ~MB scale).

## Implementation notes

### 2026-05-28 — Phase 3 execution: mike deferred

`mike` adoption was deferred to Phase 5 (release engineering) because the current docs deployment uses `actions/deploy-pages` (artifact-based, GitHub Pages source = "GitHub Actions"), while `mike` requires the source to be set to "Deploy from a branch (gh-pages)". The switch is a one-time manual repo setting change and is best synchronized with the first tagged release that needs versioned docs (the v0.4.0 cut, when `release-please` lands per [ADR-0005](0005-release-engineering.md)).

What shipped in Phase 3:

- `docs/site/dod.md` — Definition of Done page with explicit, checkable criteria for "production-grade".
- `docs/site/adrs.md` — index page listing all 8 ADRs with links to the GitHub-hosted source. Chose this over rendering the ADRs inside mkdocs to avoid rewriting their internal relative links (which reference `../../src/...` and only resolve in GitHub's view).
- mkdocs nav updated to surface both pages.

What is deferred until Phase 5:

- `mike` installation as a dev dep.
- `docs.yml` rewrite for versioned deploy via `mike deploy --push <version> latest`.
- One-time `gh api repos/<owner>/<repo>/pages -X POST -f source[branch]=gh-pages -f source[path]=/` (or equivalent UI flip).
- Initial bootstrap deploy as `dev` alias on the first push after migration.

## References

- [mike](https://github.com/jimporter/mike) — docs versioning
- [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) — theme
- [Diátaxis framework](https://diataxis.fr/) — for organizing the 4 doc types (tutorial, how-to, reference, explanation)
- ADR-0001 — the architecture decision this strategy documents
