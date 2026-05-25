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
git clone https://github.com/jovandyaz/pycenote.git
cd pycenote
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

cenote uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via GitHub OIDC. The release workflow (`.github/workflows/release.yml`) fires on any `v*` tag push and publishes to PyPI automatically.

```bash
# Bump version in pyproject.toml if needed
# Update CHANGELOG.md: move [Unreleased] items → [<version>] with date
# Commit + push:
git commit -am "release: v0.1.0"
git push origin main

# Tag + push tag (triggers release workflow):
git tag -a v0.1.0 -m "First public release"
git push --tags
```

The workflow builds wheel + sdist, verifies the import works, and publishes to <https://pypi.org/project/pycenote/>. No API tokens needed — OIDC trust is established via the pending publisher registration on PyPI (one-time setup at <https://pypi.org/manage/account/publishing/>).

## Where to ask questions

- Bugs / feature requests: <https://github.com/jovandyaz/pycenote/issues>
- Security: see [SECURITY.md](SECURITY.md)
