# ADR-0005 — Release engineering: OIDC + Sigstore + automated changelog

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

Today (v0.3.0) we have:
- Trusted Publishing via OIDC (no API tokens; publishes to PyPI on `v*` tag)
- Manual version bump in `pyproject.toml`, manual CHANGELOG entry, manual tag
- `release.yml` workflow triggers on tag push
- Single-line conventional commit messages enforced by convention (no automation)
- Releases committed directly to `main` (no PR-based release per [CONTRIBUTING.md](../../CONTRIBUTING.md))

Friction points observed in M1.0 → M1.2 cycle:
- Three opportunities for human error per release (version bump, CHANGELOG line, tag).
- CHANGELOG entries written from memory; sometimes the "why" is lost.
- No traceable link between a tag, the commits it includes, and the SBOM/wheel artifacts.

## Decision

Adopt **automated release engineering** in three independently-revertible steps:

### Step 1 — Sigstore wheel signing (auto-applied — see Implementation notes)

Original plan called for adding `sigstore/gh-action-sigstore-python@v3` explicitly. Superseded: `pypa/gh-action-pypi-publish` (already in use) auto-applies Sigstore attestations via PEP 740 when invoked with Trusted Publishing. No explicit step needed. See Implementation notes below.

### Step 2 — SBOM generation in release workflow (immediate)

Add a step that runs `cyclonedx-py uv > sbom.cdx.json` and uploads it as a GitHub Release asset. SBOM links each release to its exact dependency tree.

### Step 3 — Automated version + changelog (release-please)

Adopt `googleapis/release-please-action` to:
- Parse conventional commit messages on `main` since last release.
- Auto-generate a PR that bumps `pyproject.toml` version, updates `CHANGELOG.md`, and tags on merge.
- Maintainer reviews the PR (still human-in-the-loop), merges, tag fires → existing release workflow runs unchanged.

This **does not** replace the maintainer's judgment: it pre-fills the PR; the maintainer can edit. Removes typing the same lines manually.

### Step 4 — Reproducible builds (medium-term)

Pin Docker images in CI by digest (see ADR-0002). Document the `uv export` step that pins all transitive deps in `uv.lock` (already done implicitly — surface in docs).

## Alternatives considered

**`python-semantic-release`** instead of `release-please`. Equivalent functionality; `release-please` has wider adoption (Google's tool, used by gRPC, Bazel, etc.) and supports more languages if we ever go monorepo with non-Python packages.

**`auto`** (npm-ecosystem release tool with Python plugin). Less Python-native, weaker conventional-commits parsing.

**Fully manual releases.** Current state. Doesn't scale past ~6 releases/year before someone forgets a step.

**Pure tag-based releases without a PR** (just `git tag v0.4.0 && git push --tags`). Loses the audit trail of "what changed" pre-tag. Rejected.

**Skip Sigstore until v1.0.** Possible. We accept now because cost is low (1 GitHub action), benefit is forward-compatibility with PEP 740 attestation discovery.

## Consequences

**Positive**:
- Releases become PR-reviewed (auditable diff of what's about to ship).
- CHANGELOG fed by conventional commits; less risk of "we shipped X but forgot to document it".
- Sigstore + SBOM make the release artifact chain verifiable end-to-end.
- Maintainer time per release drops from ~15 min to ~3 min (review + merge).

**Negative**:
- `release-please` opens a PR after every commit to `main`. Mitigation: PR is a single rolling "Release v0.X.Y" PR that updates itself.
- Conventional commit discipline must be enforced; sloppy commit messages → bad CHANGELOG. Mitigation: pre-commit hook validating commit format (`commitlint` or `gitlint`).
- Sigstore bundles add ~10 KB per wheel to PyPI download size. Negligible.

**Neutral**:
- The `release-please` PR is the only PR in the repo (other commits remain direct-to-main per [CONTRIBUTING.md](../../CONTRIBUTING.md)). Inconsistent but pragmatic.

## Implementation notes

### 2026-05-28 — Phase 1 execution

- **Sigstore signing**: confirmed auto-applied by `pypa/gh-action-pypi-publish` via PEP 740 attestations on Trusted Publishing. No `sigstore/gh-action-sigstore-python` step added to `release.yml`. The release workflow now generates SBOM and attaches it to the GitHub Release; Sigstore happens transparently in the publish step.
- **SBOM**: generated via `./scripts/generate_sbom.sh` (introduced Phase 0) and uploaded to the GitHub Release via `softprops/action-gh-release@v3`.
- **release-please + reproducible builds + gitlint**: deferred to Phase 5 per the foundation-hardening plan.

### 2026-05-28 — Phase 5 execution

- **release-please-action wired** (v5.0.0): `release-please-config.json` + `.release-please-manifest.json` + `.github/workflows/release-please.yml`. Uses `pull-request-title-pattern: "chore: release ${version}"` so the eventual squash-merge commit on `main` passes the project gitlint regex (allowed prefix `chore`).
- **gitlint commit-msg hook** (v0.19.1): added to `.pre-commit-config.yaml` with project regex `^(feat|fix|chore|docs|test|refactor|perf|ci|build|style)(\([\w-]+\))?: .+`. Activated locally via `pre-commit install --hook-type commit-msg`. Note: the original Phase 5 implementation shipped a double-backslash regex that the wrap-up adversarial verify caught and corrected before commit.
- **Reproducible builds** (ADR Step 4): already satisfied by Phase 0 (Docker digest pinning per ADR-0002) and `uv.lock` committed at repo root. No new action needed.
- **mike adoption**: deferred to maintainer action per ADR-0004 cross-reference; runbook at [docs/operations.md](../../docs/operations.md).

## References

- [release-please](https://github.com/googleapis/release-please)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) — auto-signs via Sigstore on Trusted Publishing
- [PEP 740](https://peps.python.org/pep-0740/) — index support for digital attestations
- ADR-0002 (security tooling) — Sigstore + SBOM appear in both, intentional overlap
