# ADR-0002 — Multi-layer security tooling (SAST, SCA, signing, SBOM)

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

cenote is positioned as production-grade for verticals (cfdi-agent) where security posture is contractual (fiscal data, SAT compliance, audit trails). EU CRA and US Executive Order 14028 push SBOM and signed artifacts toward de-facto industry baseline by 2026-2027.

Today (v0.3.0) we have:
- `pip-audit --strict` in CI ([.github/workflows/ci.yml:37-54](../../.github/workflows/ci.yml#L37-L54))
- Dependabot with grouping ([.github/dependabot.yml](../../.github/dependabot.yml))
- Trusted Publishing (OIDC) for PyPI releases
- Apache-2.0 + SPDX headers ([CONTRIBUTING.md](../../CONTRIBUTING.md))

Gaps:
- No SAST (no CodeQL / Semgrep)
- No supplementary SCA (`pip-audit` covers PyPI; `osv-scanner` adds GHSA + OSV)
- No artifact signing (Sigstore / PEP 740)
- No SBOM
- No security linting in the editor loop (ruff rule `S` / bandit)
- Docker image pinned by mutable tag (`pgvector/pgvector:pg16`), not digest

## Decision

Adopt the following security tooling in **phased order**, each independently revertible:

### Phase 0 (immediate, low cost)

1. **Enable ruff rule set `S`** (bandit-equivalent) in `pyproject.toml` `[tool.ruff.lint] select`. Fixes likely cosmetic but signals enforcement.
2. **Pin Docker images by digest** in `.github/workflows/ci.yml` and `docker-compose.test.yml`. `pgvector/pgvector:pg16` → `pgvector/pgvector@sha256:<digest>`.
3. **Generate SBOM** with `cyclonedx-py` from `uv.lock` as a release artifact. CycloneDX is the OWASP standard.

### Phase 1 (security hardening)

4. **CodeQL** workflow (GitHub-native, free for public repos). Catches SQL injection, command injection, hardcoded secrets, weak crypto patterns.
5. **OSV-Scanner** as an additional CI step. Cross-references GHSA + OSV.dev, catches advisories `pip-audit` misses (Go modules, Cargo if Rust extensions land later).
6. **Sigstore signing** of wheels/sdists via the `sigstore/gh-action-sigstore-python` action. PEP 740-compatible. Pairs with the existing OIDC Trusted Publishing.

### Phase 2 (optional)

7. **`reuse-tool`** in CI to enforce SPDX headers (today the convention is informal).
8. **`semgrep`** (custom rules) only if specific patterns emerge (e.g., "never construct SQL via f-strings outside `pgvector_migrations`"). Defer until concrete need.

## Alternatives considered

**Snyk / Sonatype IQ / commercial SCA.** Rejected for open-source repo: free tier insufficient and ties us to a vendor.

**Bandit standalone.** Superseded by ruff rule `S` (which is bandit ported to ruff's AST). Less duplication.

**SLSA L3+ in-toto attestations.** Overkill for current maturity. Sigstore provides L2-equivalent attestations via the GitHub OIDC trust root. Revisit at v1.0.

**Container image scanning (`trivy`, `grype`).** Not applicable — we ship a wheel, not a container.

## Consequences

**Positive**:
- Coverage of three independent threat models: code patterns (CodeQL/ruff S), dependency CVEs (pip-audit + OSV-Scanner), supply chain (Sigstore + SBOM).
- Each tool is single-purpose and can be removed if it becomes noisy without affecting the rest.
- SBOM + Sigstore positions the project ahead of EU CRA enforcement (~2027).

**Negative**:
- 4 new CI jobs adds ~3-5 min to PR feedback. Mitigation: most run in parallel.
- CodeQL has higher false-positive rate than ruff for Python; need triage discipline. Mitigation: start with default rule set, only tune after 2-3 false positives.
- Pinning Docker by digest requires manual updates on `pgvector` upgrades; Dependabot doesn't natively bump Docker digests in compose. Mitigation: monthly manual review (low frequency).

**Neutral**:
- Sigstore signing creates a `.sigstore` bundle next to each wheel on PyPI. Users can verify with `python -m sigstore verify`. No-op for users who don't.

## References

- [PEP 740](https://peps.python.org/pep-0740/) — Index support for digital attestations
- [SLSA framework](https://slsa.dev/) — supply chain levels
- [OWASP CycloneDX](https://cyclonedx.org/) — SBOM standard
- EU CRA — Cyber Resilience Act (in transition)
