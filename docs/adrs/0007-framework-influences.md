# ADR-0007 — Framework influences and what to take from each

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

cenote's positioning is *not* "alternative to LangChain". LangChain is a 100k-star kitchen-sink framework solving the *integration breadth* problem. cenote solves the *production-discipline* problem for teams that hit framework complexity ceilings.

That said, no framework is built in a vacuum. Other projects have solved overlapping problems better than we ever will. Picking influences explicitly (and writing them down) prevents two failure modes:

1. **Unconscious convergence on the wrong reference.** If "RAG framework" defaults to "LangChain" in our minds, we'll keep solving LangChain's problems instead of ours.
2. **Reinventing patterns badly.** Haystack's `Pipeline` is well-thought-out; DSPy's `Module` is academically rigorous. We can borrow without depending.

## Decision

Use the following references **selectively** — adopt patterns, not dependencies. Each reference contributes to a specific cenote subsystem.

### Primary architectural references

| Reference | What to take | Where it lands in cenote | What NOT to take |
|---|---|---|---|
| **`llama-index-core`** | The `core` vs `integrations` split pattern for monorepo | ADR-0008 (monorepo strategy) | Their `Service` registry — overkill for our scale |
| **`haystack-ai`** (Deepset) | `Component` Protocol + declarative `Pipeline.connect(a, b)` orchestration | `cenote.pipeline.IndexingPipeline` (Phase 4) | Their YAML pipeline config — we prefer code-as-config |
| **`txtai`** | Minimalism + Postgres-first defaults | Validation of our overall direction | Their bundled UI/server — out of scope |
| **`paradedb`** | "Less abstractions, more Postgres" philosophy | `PgBM25Retriever` using `tsvector` (M1.3 Cluster C) | Their full Postgres extension — different scope |

### LLM and agent references

| Reference | What to take | Where it lands |
|---|---|---|
| **`dspy`** (Stanford) | `Signature` Protocol (declarative I/O for LLM modules), `Module`/`Predict` separation | `cenote-agent` (M2.0+) for agent contracts |
| **`langgraph`** (already in stack per [CLAUDE.md](../../CLAUDE.md)) | State machines with conditional edges, checkpointing model | `cenote-agent` runtime — depend on it, don't reimplement |
| **`instructor`** (Jason Liu) | Tool use with Pydantic, opt-in decoration over plain `complete()` | `AnthropicLLM.tool_use()` (M1.3) — possibly *depend* on `instructor` if it stays minimal |
| **`marvin`** (Prefect) | Minimal LLM tooling primitives | Conceptual — keep our API surface small |

### Python library design references

| Reference | What to take | Where it lands |
|---|---|---|
| **`httpx`** | Protocol design + sync/async parity discipline + transport composition | Already mirrored in our Protocols; reinforce |
| **`asyncpg`** | Async API design + low-level performance attitude | Already a dep; study their patterns for our own code |
| **`anyio`** | Trio-compatible async layer (if we ever want trio support) | Defer — only if a real user demands trio |
| **`pydantic-core`** | Rust+Python packaging via PyO3 + maturin | Defer — only if a hot path measurably benefits (e.g., BM25 tokenizer, vector ops) |
| **`pydantic`** itself | `ConfigDict(extra="forbid")` discipline + Protocol-friendly model design | Already adopted in [src/cenote/models.py](../../src/cenote/models.py) |

### Benchmarking and evaluation references

| Reference | What to take |
|---|---|
| **BEIR** (benchmark) | Dataset format, qrels structure, metric definitions |
| **MTEB** (Massive Text Embedding Benchmark) | Per-language embedding leaderboards — target for cenote's eval reports |
| **`ranx`** (lib) | Statistical significance testing for retrieval (paired t-test, bootstrap CI) — adopt if we publish leaderboards |
| **MIRACL** (dataset) | Already used in [cenote.eval.datasets](../../src/cenote/eval/datasets/) for ES/EN |

### What we explicitly do NOT take from

| Reference | Why not |
|---|---|
| **`langchain`** (any package) | Filosofía opuesta. Their `Runnable` abstraction leaks. Their chain-of-many-deps is the problem we exist to avoid. |
| **`crewai`** | Strong opinions on multi-agent orchestration that don't fit our Protocol model |
| **`autogen`** (Microsoft) | Heavy framework, opinionated on conversation patterns |
| **`semantic-kernel`** (Microsoft) | Plugin-system-oriented; doesn't match our protocol-first design |

## How to use this ADR

When designing a new subsystem:

1. Find the cell in the tables above that maps to your subsystem (e.g., "I'm building agents" → DSPy + LangGraph).
2. Read the relevant reference's design docs/source (don't import unless `instructor`-style minimal).
3. Cite the influence in the implementation's module docstring (e.g., *"Pipeline design inspired by haystack-ai's Component model"*).
4. If your design diverges from the reference, write a one-line *"why we differ"* in the docstring or a new ADR.

## Alternatives considered

**Pick one reference framework and stay close to it.** Risk: ties our roadmap to theirs. We want cherry-pick freedom.

**Pick no references; design from scratch.** Risk: reinvent badly. Most patterns we need already exist.

**Document influences in code comments only.** Risk: ad-hoc, not citable. ADRs make the influence map deliberate.

## Consequences

**Positive**:
- Future contributors know *which* references are blessed and *what* to take from each. Reduces analysis-paralysis on design choices.
- Avoids the failure mode where we accidentally clone LangChain because "everyone else does".

**Negative**:
- The reference list will age. Re-evaluate annually.
- Some readers may interpret this as endorsement of *depending on* these libs; the table makes the distinction explicit (most are pattern-references, only a few are deps).

**Neutral**:
- This ADR has the highest churn rate of any in this batch — expect supersession every 12-18 months as the AI/RAG landscape moves.

## References

- [haystack-ai docs](https://docs.haystack.deepset.ai/) — `Pipeline` model
- [llama-index-core README](https://github.com/run-llama/llama_index/tree/main/llama-index-core) — core/integrations split
- [DSPy paper](https://arxiv.org/abs/2310.03714) — declarative LLM programs
- [instructor docs](https://python.useinstructor.com/) — minimal tool use
- [paradedb](https://www.paradedb.com/) — Postgres-native search
- ADR-0006 — dependency selection criteria
