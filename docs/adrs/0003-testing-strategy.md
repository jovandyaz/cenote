# ADR-0003 — Testing strategy: unit + property + benchmark + integration

**Status**: Accepted
**Date**: 2026-05-28
**Deciders**: Jovan Díaz

## Context

Today (v0.3.0) we have:
- 254 unit tests + 11 integration tests (Postgres + pgvector via Docker)
- Coverage tracked via Codecov, no threshold enforcement
- `pytest-asyncio` for async, `pytest-cov` for coverage
- `respx` for HTTP mocking
- Test factories ([tests/_factories.py](../../tests/_factories.py)) + stubs ([tests/_stubs.py](../../tests/_stubs.py))

Gaps:
- No property-based testing. Hand-written cases miss edge cases that property tests find (e.g., a chunker invariant like *"concat of chunks contains original content"* — easy to write as a property, painful to enumerate as examples).
- No performance benchmarking. Claims like *"WAL mode gives ~10x batch-write throughput"* live in docstrings without enforcement; regressions are silent.
- No coverage threshold. PRs can drop coverage from 92% to 80% silently.
- Mutation testing absent. We don't know if our 254 tests would catch real mutations.

## Decision

Adopt a **layered testing strategy** with explicit purpose per layer:

| Layer | Tool | Purpose | When |
|---|---|---|---|
| Unit | `pytest` | Function/class behavior on representative inputs | Every PR |
| Property | `hypothesis` | Invariants over auto-generated inputs | Every PR (where applicable) |
| Integration | `pytest -m integration` | End-to-end with Postgres + pgvector | Every PR (separate job) |
| Benchmark | `pytest-benchmark` | Perf regression gating | Every PR (compare to baseline) |
| Smoke | `tests/demos/test_quickstart_smoke.py` | The README example actually runs | Every PR |

Specifics:

1. **`pytest-benchmark`** added to dev deps. Golden baselines committed under `tests/benchmarks/baselines/`. CI fails if a perf regression exceeds 25% on any benchmark.

2. **`hypothesis`** added to dev deps. Property tests added for:
   - **Chunkers**: invariants like *concat-coverage*, *chunk_size bound*, *overlap bound*, *idempotence on `chunk(chunk_output_concat)`*.
   - **HybridRetriever RRF**: monotonicity of score in rank, weight sensitivity, dedupe correctness.
   - **SpanishTokenizer**: `fold(fold(x)) == fold(x)`, stopword filtering idempotence, stemming determinism.
   - **EmbeddingCache**: get-after-set returns set value, set-many equivalent to N set, model_id isolation.

3. **Coverage threshold** enforced in CI: `pytest --cov-fail-under=80`. Start at 80%, ratchet to 85% after Phase 1 completes.

4. **Mutation testing**: deferred. Re-evaluate after Phase 2 — if test quality is questioned, run `mutmut` ad-hoc.

5. **Test categorization** via pytest markers (already partial):
   - `@pytest.mark.integration` — needs Postgres (existing)
   - `@pytest.mark.slow` — runtime > 1s
   - `@pytest.mark.benchmark` — perf gating
   - `@pytest.mark.network` — needs external API (skipped by default)

## Alternatives considered

**`tox` for multi-env testing.** uv handles this via `--python` matrix; tox adds an extra config layer with no benefit at our scale.

**`schemathesis` for API contract testing.** Not applicable — cenote is a library, not an HTTP service.

**`coverage --branch` only.** Already enabled in [pyproject.toml:119](../../pyproject.toml#L119) (`branch = true`). Keep.

**Property testing with `crosshair`.** Too experimental (uses SMT solver). Stick to `hypothesis`.

**`pytest-xdist` for parallel test execution.** Worth adopting if test suite crosses ~60s wall-clock. Today it's fast enough.

## Consequences

**Positive**:
- Property tests will catch entire bug categories (e.g., off-by-one in chunker overlap, RRF tie-breaking) that hand-written tests miss.
- Benchmark regressions become CI failures, not deferred deuda.
- Coverage threshold prevents quiet quality decay.

**Negative**:
- Property tests can flake if generators produce pathological inputs. Mitigation: use `hypothesis`'s shrinking + `@settings(max_examples=N)` to cap runtime.
- `pytest-benchmark` baselines must be stored *somewhere* (git-tracked in `tests/benchmarks/baselines/` JSON files). Baselines drift over time and require periodic rebaseline.
- 80% threshold may force tests for trivial code paths (`__init__.py` exports). Mitigation: `--cov-config` exclusions for known low-value paths.

**Neutral**:
- Mutation testing remains a future option. If it ever runs and finds gaps, we add tests; we don't gate CI on `mutmut` scores (high noise).

## References

- [Hypothesis docs — Properties of Good Tests](https://hypothesis.readthedocs.io/en/latest/quickstart.html)
- [pytest-benchmark docs](https://pytest-benchmark.readthedocs.io/)
- [src/cenote/chunkers/recursive.py](../../src/cenote/chunkers/recursive.py) — first target for property tests
- [src/cenote/retrievers/hybrid.py](../../src/cenote/retrievers/hybrid.py) — second target
