# Contributing to cenote

cenote is in early development and not yet accepting external pull requests for features. Bug reports, security disclosures (see [SECURITY.md](SECURITY.md)), and documentation improvements are welcome via GitHub Issues.

## Goals

- Production-grade RAG primitives in idiomatic Python 3.12+
- Type-strict (`mypy --strict` clean), Protocol-based, multi-tenant by design
- Narrow surface — no kitchen-sink integrations
- Spanish/LATAM-aware roadmap (M1.1+)

If you're not sure whether a change aligns with these goals, open an issue first.

## Development setup

Prerequisites: Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/) 0.5+.

```bash
git clone https://github.com/jovandyaz/cenote.git
cd cenote
uv sync --all-extras
uv run pre-commit install
```

## Running tests

```bash
# Unit tests (fast, no Docker)
uv run pytest -m "not integration"

# Unit tests with coverage report
uv run pytest -m "not integration" --cov=cenote --cov-report=term-missing

# Integration tests (require Postgres + pgvector via Docker)
docker compose -f docker-compose.test.yml up -d
uv run pytest -m integration -v
docker compose -f docker-compose.test.yml down -v

# Full check suite (matches CI)
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -m "not integration"
uv run pre-commit run --all-files
```

## Code style

- **License header**: every `.py` file under `src/` starts with `# SPDX-License-Identifier: Apache-2.0` as the first non-empty line, before the module docstring. Test files exempt.
- **Type hints**: `mypy --strict` must pass. Public functions and class methods need annotations.
- **Docstrings**: Google style. Public API gets 1-3 line docstrings stating contract. Inline `# WHY` comments only when the constraint is non-obvious.
- **Pydantic v2 syntax**: use `model_config = ConfigDict(...)`, not the v1 `class Config:` inner class.
- **Async by default** for I/O-bound paths. Sync only when wrapping inherently-sync libraries.
- **No new top-level dependencies without discussion**. Open an issue first describing the name, version, license, and alternatives considered.

## Commit conventions

- Conventional Commits: `feat(scope):`, `fix(scope):`, `chore(scope):`, `docs(scope):`, `test(scope):`, `refactor(scope):`, `ci(scope):`.
- **Single-line commit messages, no body.** Detailed context lives in the PR description (or the CHANGELOG, since we currently commit directly to main).
- Imperative mood: "add X", not "added X" or "adds X".
- Subject line under 72 characters.

## Release process

Releases are automated with [release-please](https://github.com/googleapis/release-please) and PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (GitHub OIDC). There is no manual tagging.

1. Land conventional-commit work on `main` (`feat:` / `fix:` / `docs:` … — see above). release-please opens or updates a `chore: release X` PR that bumps `pyproject.toml`, regenerates `CHANGELOG.md`, and syncs `uv.lock`.
2. Merge that PR. release-please tags `vX.Y.Z`, and the `publish` job builds wheel + sdist, verifies the import in an isolated venv, attaches a CycloneDX SBOM, and publishes to <https://pypi.org/project/cenote-core/> with PEP 740 Sigstore attestations.

No API tokens needed — OIDC trust is the pending-publisher registration on PyPI (one-time setup at <https://pypi.org/manage/account/publishing/>). `.github/workflows/release.yml` remains as a manual `workflow_dispatch` fallback to re-publish an existing tag.

## Where to ask questions

- Bugs / feature requests: <https://github.com/jovandyaz/cenote/issues>
- Security: see [SECURITY.md](SECURITY.md)
