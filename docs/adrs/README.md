# Architecture Decision Records

This directory contains the **Architecture Decision Records (ADRs)** for the cenote project. Each ADR captures a single architecturally-significant decision: the context that forced it, the decision itself, alternatives considered, and the consequences.

## Why ADRs

Decisions decay in oral form. A year from now, the question *"why did we pick Protocols over ABCs?"* will have a worse answer if it lives only in chat history or scattered docstrings. ADRs make the reasoning durable, citable, and revisable.

## Format

Each ADR follows the Michael Nygard template:

```
# ADR-NNNN — Short title

Status: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
Date: YYYY-MM-DD
Deciders: <names>

## Context
Forces at play, constraints, what triggered the decision.

## Decision
What we decided. State it imperatively, present tense.

## Alternatives considered
What else was on the table and why it lost.

## Consequences
Positive, negative, neutral. Be honest about the trade-offs.

## References
Links to PRs, issues, papers, prior ADRs.
```

## When to write an ADR

- Picking between architectural patterns (Protocol vs ABC, sync vs async, layered vs hex).
- Adopting a non-trivial dependency that changes how downstream code is written.
- Reversing a previous decision (creates a new ADR that supersedes the old one).
- A reader 18 months from now would ask *"why is it this way?"* and the code alone wouldn't answer.

## When NOT to write an ADR

- Bug fixes, refactors that don't change architecture, dependency version bumps.
- Decisions that are obvious from the code (variable names, file structure).
- Anything covered by `CLAUDE.md` conventions.

## Lifecycle

1. **Proposed** — open a PR with status `Proposed`. Discuss in the PR.
2. **Accepted** — merge when consensus is reached. Code can now rely on it.
3. **Deprecated** — keep the file, change status, write a new ADR explaining why.
4. **Superseded** — change status to `Superseded by ADR-NNNN`.

ADRs are append-only. Never delete or edit an accepted ADR's *decision*; if it changes, write a new one.

## Index

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-architecture-protocols-and-layers.md) | Layered architecture with Protocol-based interfaces | Accepted | 2026-05-28 |
| [0002](0002-security-tooling.md) | Multi-layer security tooling (SAST, SCA, signing, SBOM) | Accepted | 2026-05-28 |
| [0003](0003-testing-strategy.md) | Testing strategy: unit + property + benchmark + integration | Accepted | 2026-05-28 |
| [0004](0004-documentation-strategy.md) | Documentation strategy: mkdocs + mike + ADRs | Accepted | 2026-05-28 |
| [0005](0005-release-engineering.md) | Release engineering: OIDC + Sigstore + automated changelog | Accepted | 2026-05-28 |
| [0006](0006-dependency-selection.md) | Dependency selection criteria and current choices | Accepted | 2026-05-28 |
| [0007](0007-framework-influences.md) | Framework influences and what to take from each | Accepted | 2026-05-28 |
| [0008](0008-monorepo-strategy.md) | Monorepo strategy for cenote-core, cenote-agent, cenote-X | Proposed | 2026-05-28 |
