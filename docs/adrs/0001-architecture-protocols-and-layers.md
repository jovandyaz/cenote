# ADR-0001 — Layered architecture with Protocol-based interfaces

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

cenote is the shared core for downstream products that demand opposite qualities (knowtis-ai needs creative synthesis; cfdi-agent needs deterministic auditability). The framework must:

1. **Compose**, not constrain — users mix any chunker with any embedder with any store.
2. **Be implementable from outside** the repo — users can drop in their own concrete impl without inheriting from us.
3. **Be type-strict** — `mypy --strict` clean so wiring errors surface in CI, not production.
4. **Stay small** — narrow surface so the library is easy to read end-to-end.
5. **Enforce multi-tenancy by construction** — cross-tenant leakage must be impossible by API shape, not by convention.

Without an explicit architecture decision, ad-hoc growth would converge on either (a) deep inheritance hierarchies (LangChain pre-`langchain-core`) or (b) a single monolithic class per concern.

## Decision

cenote uses a **5-layer architecture** (`models` → `chunkers` → `embedders` → `stores` → `retrievers`, plus orthogonal `observability`, `llm`, `eval`, `rerankers`, `tokenizers`) where every layer exposes a `typing.Protocol` and concrete implementations satisfy it **structurally** (no inheritance from the protocol).

Composition is the only extension mechanism. Cross-cutting concerns (tracing, caching) are wrappers that satisfy the same Protocol as their inner object (`TracedEmbedder`, `CachedEmbedder`).

Multi-tenancy is enforced at the Protocol level: `namespace: str` is a required positional/keyword argument on every method that touches data (`VectorStore.upsert`, `VectorStore.search`, `Retriever.retrieve`, etc.).

## Alternatives considered

**a) ABCs with inheritance.** The historical Python pattern. Rejected because (i) consumers must inherit our class, creating a tight coupling and import order issues, (ii) it prevents structural duck-typing, (iii) it discourages composition (decorators) and pushes toward inheritance chains.

**b) Hexagonal architecture / ports & adapters with explicit DI container.** Rejected because it adds a runtime container (zero standardization in Python; `dependency-injector`, `lagom`, etc. each have idiosyncrasies) and the boundary clarity benefit is already provided by Protocol + module layering.

**c) Single mega-class per concern (e.g., one `Indexer` class).** Rejected because it forces every variation into kwargs/strategies, gets unmanageable past 2-3 axes, and breaks the Open/Closed principle.

**d) Effect systems / Result types (à la Rust, Haskell).** Rejected for ergonomic mismatch with Python and the cost of teaching consumers. Errors as exceptions are the Python idiom.

## Consequences

**Positive**:
- Users can implement any Protocol from outside without importing cenote at the type level (only at runtime, if at all).
- Composition wrappers (`TracedX`, `CachedX`) follow the same shape as the inner object — no special API needed.
- Multi-tenancy bugs become *type errors*, not runtime errors. A caller that forgets `namespace=` fails mypy.
- The architecture is **readable end-to-end in an afternoon** — there is no hidden dependency graph.

**Negative**:
- Protocols don't enforce method *bodies*. A consumer can satisfy `Embedder` with `async def embed(...): return []` and the framework can't reject it. Mitigation: integration tests, runtime assertions in critical paths only.
- Static typing of Protocols requires Python 3.12+ for the cleanest syntax (`type X = ...`); we already require 3.12.
- Composition wrappers can stack to confusing depth (`TracedCachedEmbedder` → `CachedEmbedder` → `VoyageEmbedder`). Mitigation: don't auto-stack; let users compose explicitly.

**Neutral**:
- Future evolution: add a `Pipeline` orchestrator (ADR-NNNN, future) that *consumes* Protocols but does not *replace* them. The Protocol layer remains foundational.
- Boundary enforcement: today layer boundaries are convention. Future: adopt `tach` or `grimp` to fail CI when `chunkers/` imports `stores/` (or similar inversions).

## References

- [src/cenote/embedders/base.py](../../src/cenote/embedders/base.py) — canonical Protocol example
- [src/cenote/observability/wrappers.py](../../src/cenote/observability/wrappers.py) — composition wrappers
- [src/cenote/stores/base.py](../../src/cenote/stores/base.py) — multi-tenancy in the Protocol shape
- PEP 544 (Protocols)
- *Architecture Patterns with Python* — Percival & Gregory, on layered + ports-and-adapters in Python
