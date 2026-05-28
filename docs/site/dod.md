# Definition of Done

A milestone is "done" when **all** these criteria are met. Anything skipped is documented in [CHANGELOG.md](changelog.md) with explicit waiver text.

This page is the contract between contributors and the maintainer: *"production-grade"* is not asserted, it is measured.

## Code quality

- [ ] `uv run ruff check .` clean
- [ ] `uv run ruff format --check .` clean
- [ ] `uv run mypy src/` clean (zero errors with `--strict`)
- [ ] `uv run pytest -m "not integration"` passes
- [ ] `uv run pytest -m integration` passes (with Docker pgvector running)
- [ ] Coverage at or above the current CI threshold (see `--cov-fail-under` in [`.github/workflows/ci.yml`](https://github.com/jovandyaz/cenote/blob/main/.github/workflows/ci.yml))
- [ ] No `# type: ignore` added without a one-line reason comment
- [ ] No `# noqa` added without a one-line reason comment

## API surface

- [ ] Every new public symbol has a docstring (Google style)
- [ ] Every new module has a module-level docstring (1-2 lines, purpose)
- [ ] `__init__.py` exports the public symbols
- [ ] `mkdocstrings` renders the new APIs without warnings

## Tests

- [ ] Unit tests cover happy path + at least 2 edge cases per new function
- [ ] Property tests added for any new pure function with invariants (idempotence, monotonicity, determinism, etc.)
- [ ] Benchmark added for any performance-claimed feature (e.g., *"WAL gives 10x throughput"* must have a benchmark backing the claim)
- [ ] Integration test added if the feature touches Postgres, HTTP, or any external service

## Documentation

- [ ] [`CHANGELOG.md`](https://github.com/jovandyaz/cenote/blob/main/CHANGELOG.md) entry follows Keep-a-Changelog format
- [ ] Each entry states **what** changed + **why** + **impact** for users
- [ ] If breaking (pre-1.0), include migration snippet
- [ ] ADR written if the change is architecturally significant (see [ADRs index](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/README.md))
- [ ] `uv run mkdocs build --strict` succeeds with zero warnings

## Dependencies

- [ ] No new runtime dependency without an updated [ADR-0006](https://github.com/jovandyaz/cenote/blob/main/docs/adrs/0006-dependency-selection.md)
- [ ] `uv.lock` committed
- [ ] `pip-audit --strict` passes (CI enforces)
- [ ] CodeQL scan green (CI enforces)
- [ ] OSV-Scanner green (CI enforces)
- [ ] SBOM generates successfully (`./scripts/generate_sbom.sh`)

## Release

- [ ] Version bumped in [`pyproject.toml`](https://github.com/jovandyaz/cenote/blob/main/pyproject.toml)
- [ ] Tag follows `v<major>.<minor>.<patch>` convention
- [ ] Trusted Publishing workflow ran green
- [ ] Sigstore attestations auto-applied via `pypa/gh-action-pypi-publish` (PEP 740)
- [ ] SBOM attached to GitHub Release as asset
- [ ] mkdocs deployed (per current docs workflow; versioned deploy via mike lands in Phase 5)

## Verification

Run the per-phase verify scripts to confirm tooling still works end-to-end:

```bash
./scripts/verify/phase0.sh  # security + tooling baseline
./scripts/verify/phase1.sh  # SAST + SCA + signing + SBOM
./scripts/verify/phase2.sh  # property tests + benchmarks + coverage
```

These are **not** part of CI gating — they are manual safety nets for the maintainer.

## When to waive a criterion

Some criteria don't apply universally (e.g., a docs-only PR doesn't need integration tests). When skipping, **state the reason in the commit message or PR description**:

```text
chore: bump dev dep mkdocstrings 1.10 → 1.11

DoD waivers:
- Integration tests not run (no runtime code changed)
- No CHANGELOG entry (dev-only dep, not user-facing)
```

Silent waivers are a smell. Stating them keeps the bar honest.
