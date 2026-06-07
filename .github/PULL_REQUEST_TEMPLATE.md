## Summary

<!-- What does this change, and why? Link any related issue. -->

## Checklist

- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy src/` passes (`--strict`)
- [ ] `uv run pytest -m "not integration"` passes; new code has tests
- [ ] New `src/` files start with `# SPDX-License-Identifier: Apache-2.0`
- [ ] Conventional-commit subject (`feat:`, `fix:`, `docs:`, …), single line
- [ ] CHANGELOG / docs updated if user-facing
