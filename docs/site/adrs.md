# Architecture Decision Records

cenote uses **Architecture Decision Records (ADRs)** to capture significant architectural decisions: why a path was chosen, what alternatives were considered, and what the consequences are. ADRs are durable, citable, and append-only — they make the reasoning behind the codebase explorable years later.

The ADRs live in [`docs/adrs/`](https://github.com/jovandyaz/cenote/tree/main/docs/adrs) in the source repo. They are intentionally **not** rendered inside this docs site because they reference internal file paths and the GitHub view preserves those links naturally.

## Format

Each ADR follows the Michael Nygard template: Context · Decision · Alternatives · Consequences · References. See the [ADRs README](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/README.md) for the full lifecycle.

## Index

| # | Title | Status |
|---|---|---|
| [0001](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0001-architecture-protocols-and-layers.md) | Layered architecture with Protocol-based interfaces | Accepted |
| [0002](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0002-security-tooling.md) | Multi-layer security tooling (SAST, SCA, signing, SBOM) | Accepted |
| [0003](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0003-testing-strategy.md) | Testing strategy: unit + property + benchmark + integration | Accepted |
| [0004](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0004-documentation-strategy.md) | Documentation strategy: mkdocs + mike + ADRs | Accepted |
| [0005](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0005-release-engineering.md) | Release engineering: OIDC + Sigstore + automated changelog | Accepted |
| [0006](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0006-dependency-selection.md) | Dependency selection criteria and current choices | Accepted |
| [0007](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0007-framework-influences.md) | Framework influences and what to take from each | Accepted |
| [0008](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0008-monorepo-strategy.md) | Monorepo strategy for cenote-core, cenote-agent, cenote-X | Proposed |

## When to write a new ADR

- Picking between architectural patterns (Protocol vs ABC, sync vs async, layered vs hex).
- Adopting a non-trivial dependency that changes how downstream code is written.
- Reversing a previous decision (creates a new ADR that supersedes the old one).
- A reader 18 months from now would ask *"why is it this way?"* and the code alone wouldn't answer.

Routine code changes (bug fixes, refactors, dep version bumps) do **not** warrant an ADR.
