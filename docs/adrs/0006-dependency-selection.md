# ADR-0006 — Dependency selection criteria and current choices

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

cenote's positioning ("narrow surface, no kitchen sink") makes every new dependency a meaningful commitment. Once a dep is in `pyproject.toml`, removing it later requires a major version bump (per pre-1.0 disclaimer, until v1.0; thereafter SemVer-strict).

We need a **predictable filter** that says yes or no to a candidate dep, ideally before the contributor writes the PR.

Today's deps ([pyproject.toml](../../pyproject.toml)):

| Dep | Purpose | Risk |
|---|---|---|
| `aiosqlite>=0.20` | SqliteCache backend | Low — wraps stdlib `sqlite3` |
| `anthropic>=0.39` | AnthropicLLM | Medium — vendor SDK, may break |
| `asyncpg>=0.30` | PgVectorStore | Low — de-facto async Postgres client |
| `httpx>=0.27` | HTTP for Voyage/Cohere | Low — industry standard |
| `numpy>=2.0` | Vector ops in InMemoryVectorStore | Low — fundamental |
| `pydantic>=2.8` | Data models | Low — standard |
| `pystemmer>=2.2` | Spanish stemming | Medium — C extension, less common |
| `rank-bm25>=0.2.2` | BM25Retriever | Medium — small lib, single maintainer |

Optional extras: `opentelemetry-{api,sdk}>=1.27`, `langfuse>=2.0`.

## Decision

A candidate dependency must pass **all** of these gates:

### Gate 1 — Necessity

The dep eliminates ≥ 50 LOC of subtle code we'd otherwise write. "Subtle" means: concurrent safety, network protocols, parsing of complex formats, well-studied algorithms. Glue code doesn't count.

### Gate 2 — Health

- ≥ 50k downloads/month on PyPI (proves real-world use).
- Last release within 12 months.
- ≥ 1 commit in last 6 months OR explicit "feature complete" status from maintainer.
- License is permissive (MIT, Apache-2.0, BSD). LGPL acceptable; GPL rejected.
- Single maintainer is a yellow flag (not red). Multi-maintainer or org-backed is green.

### Gate 3 — Substitutability

If the dep disappeared tomorrow, can we replace it in < 1 day with our own code or a different lib? Yes → accept. No → think twice.

Example: `httpx` passes (could swap to `aiohttp` or stdlib `urllib` in a few hours). `langchain-core` would fail (its abstractions leak into our API shape).

### Gate 4 — Surface bleed

Does the dep's types appear in cenote's **public** API? If yes, downstream code is now coupled to that dep's versioning. Try harder to keep it internal. Currently: `httpx` is internal (only `_http.py`), `asyncpg.Pool` is **public** (PgVectorStore constructor). The asyncpg leak is an accepted trade-off (alternative: own pool wrapper, adds friction for users who already manage pools).

### Gate 5 — No new top-level dep without ADR

Per [CONTRIBUTING.md](../../CONTRIBUTING.md): a PR adding a runtime dep must reference an ADR that justifies it. Dev deps (test/lint) are exempt unless they affect contributor onboarding.

### Adoption plan for new deps (this ADR's downstream effect)

These deps **pass all gates** and are scheduled for adoption (see [Phase 1/2 in the foundation-hardening plan](../superpowers/plans/2026-05-28-foundation-hardening.md)):

| Dep | Replaces / enables | Phase | Risk |
|---|---|---|---|
| `stamina` (dev → runtime) | `_http.py` `retrying` (~40 LOC) + adds jitter | Phase 4 | Low — well-maintained, type-safe |
| `aiolimiter` (runtime) | `_http.py` `RateLimiter` (~60 LOC) | Phase 4 | Low — 5+ years, stable |
| `hypothesis` (dev) | Property tests | Phase 2 | None (dev) |
| `pytest-benchmark` (dev) | Perf gating | Phase 2 | None (dev) |
| `mike` (dev) | Docs versioning | Phase 3 | None (dev) |
| `cyclonedx-py` (dev) | SBOM generation | Phase 0 | None (dev) |

**Considered, deferred:**
- `markdown-it-py` — only if knowtis-ai demands richer Markdown (HTML inline, frontmatter, math).
- `instructor` — adopt when tool use lands in `AnthropicLLM` (M1.3).
- `msgspec` — only if hot-path JSON parsing in embedders is measured as a bottleneck.

**Rejected:**
- `langchain-*`, `litellm` — violate Gate 4 (surface bleed) and project positioning.
- `alembic` — fails Gate 1 (our 3 migrations don't need its abstractions).
- `diskcache` — fails Gate 3 (we'd lose control over our schema).
- `ragas` — opinionated on OpenAI; doesn't fit multi-provider stance.
- `dspy` — fails Gate 2 (API still unstable across 2025/2026).

## Alternatives considered

**No formal criteria, case-by-case decisions.** Status quo before this ADR. Works for a single maintainer, doesn't scale to a small team or future contributors.

**Lockstep with `llama-index-core` deps.** Tempting (proven choices), but couples our roadmap to theirs.

**"Zero deps" purism.** Rejected — implementing HTTP, async DB drivers, Pydantic-grade validation ourselves is not a good use of time.

## Consequences

**Positive**:
- Contributors have a clear answer to "should I add this dep?" without asking.
- The dependency tree stays small and curated; SBOM (per ADR-0002) stays readable.
- Risk surface tracked: every dep has known health + substitutability.

**Negative**:
- Gates 1-5 require judgment. Some good libs may be rejected if the gate is applied mechanically. Mitigation: maintainer override with written rationale in the ADR.

**Neutral**:
- Bumping a dep's major version is *not* a new dep — different ADR criteria apply (see CHANGELOG breaking-change handling).

## References

- [pyproject.toml](../../pyproject.toml) — current dep list
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — "No new top-level dependencies without discussion"
- [stamina](https://github.com/hynek/stamina) — Hynek Schlawack
- [aiolimiter](https://github.com/mjpieters/aiolimiter)
- ADR-0007 — frameworks we draw inspiration from (sometimes that means *not* depending on them)
