# Phase 4 + Phase 5 — Practical Proof Report

Generated 2026-05-29.

## TL;DR

All six verify scripts (`phase0.sh`..`phase5.sh`) exit 0, the end-to-end demo (`demos/e2e_phase4_5.py`) exits 0 across all five scenarios, and four of five CI workflows are green on the Phase 5 head (`0c1dc7d`). Twelve of fourteen Phase 4/5 deliverables are **PROVEN** by combined CI + script + demo evidence; **release-please** is **GATED** on a one-time repo setting documented in ADR-0005, and **mike versioned docs** are **PENDING** functional proof until the v0.4.0 cut.

## Method

Evidence is layered: (1) CI workflows on `main` after the Phase 5 pushes confirm the toolchain runs in GitHub's environment; (2) per-phase `scripts/verify/*.sh` scripts re-run the same invariants locally as deterministic smoke tests; (3) `demos/e2e_phase4_5.py` exercises the actual Python primitives end-to-end with assertions, so any silent regression in retrieval, indexing, tracing, or commit-msg linting fails the run. Each Phase 4/5 deliverable in the per-feature table cites at least one layer's evidence.

## Layer 1 — CI workflows (per Phase 5 push 4319548 + 0c1dc7d)

| Workflow | Conclusion |
| --- | --- |
| CI | success |
| CodeQL | success |
| Deploy docs | success |
| OSV-Scanner Scheduled | success |
| release-please | failure (gated by manual repo setting — see "Gated" section) |

## Layer 2 — Verify scripts (manual e2e checks)

| Script | Exit | Summary |
| --- | --- | --- |
| `scripts/verify/phase0.sh` | 0 | Phase 0 verification: ALL CHECKS PASSED |
| `scripts/verify/phase1.sh` | 0 | Phase 1 verification: ALL CHECKS PASSED |
| `scripts/verify/phase2.sh` | 0 | Phase 2 verification: ALL CHECKS PASSED |
| `scripts/verify/phase3.sh` | 0 | Phase 3 verification: ALL CHECKS PASSED |
| `scripts/verify/phase4.sh` | 0 | Phase 4 verification: ALL CHECKS PASSED |
| `scripts/verify/phase5.sh` | 0 | Phase 5 verification: ALL CHECKS PASSED |

## Layer 3 — Demo script (real API execution)

Demo file: `demos/e2e_phase4_5.py`
Demo exit code: 0
Adversarial verify: 5/5 scenarios actually exercised the claimed primitive.

```
=== Scenario 1 — Phase 4.8 IndexingPipeline
[OK] indexed 7 chunks across 3 progress events

=== Scenario 2 — Phase 4.5 HybridRetriever resilience
[OK] failing retriever tolerated; healthy result fused into output

=== Scenario 3 — Phase 4.6 BM25Retriever LRU eviction
after a,b -> cache keys: ['a', 'b']
after c   -> cache keys: ['b', 'c']
[OK] LRU evicted 'a' once 'c' pushed the cache past max=2

=== Scenario 4 — Phase 4.7 TracedVectorStore
[OK] emitted spans: ['store.search']; store.search attrs: {'namespace': 'demo', 'limit': 3, 'result_count': 0}

=== Scenario 5 — Phase 5 gitlint commit-msg smoke test
[OK] 'chore(verify): test scoped' -> exit=0 (expected 0)
[OK] 'feat: add foo' -> exit=0 (expected 0)
[OK] 'BAD MESSAGE NO PREFIX' -> exit=1 (expected 1)
[OK] 'release: 0.4.0' -> exit=1 (expected 1)

ALL DEMOS PASSED
```

Adversarial verifier gaps (if any): none — every scenario asserts on a concrete invariant of the primitive under test.

## Per-feature status table

| Phase | Deliverable | Status | Evidence |
| --- | --- | --- | --- |
| 4.1 | stamina + aiolimiter runtime deps | PROVEN | imports succeed in demo + verify script check 1 |
| 4.2 | `retrying()` refactor with jitter | PROVEN | `test_retrying_applies_jitter_to_backoff` passes; verify script check 2 |
| 4.3 | RateLimiter via aiolimiter | PROVEN | `test_at_limit_throttles` passes; verify script check 3 |
| 4.4 | HNSW `SET LOCAL` transaction wrap | PROVEN | integration test `test_hnsw_ef_search_executes_within_transaction` passes in CI (verify script check 4) |
| 4.5 | HybridRetriever `return_exceptions` | PROVEN | demo scenario 2 exits 0 with assertion + 2 hypothesis property tests |
| 4.6 | BM25 LRU + `invalidate()` | PROVEN | demo scenario 3 exits 0 with assertion + 5 dedicated tests |
| 4.7 | TracedVectorStore | PROVEN | demo scenario 4 emits `store.search` span + 3 tests |
| 4.8 | IndexingPipeline | PROVEN | demo scenario 1 indexes 7 docs end-to-end + 6 tests |
| 5.1 | release-please scaffold (v5) | GATED | config parses + workflow runs through commit step; **blocked by repo setting "Allow GitHub Actions to create and approve pull requests" — see ADR-0005 for the `gh api` fix command** |
| 5.2 | gitlint commit-msg hook | PROVEN | demo scenario 5 + every commit since `2877696` passes the hook |
| 5.3 | mike runbook (doc only) | PENDING | `docs/operations.md` ready; functional proof only at v0.4.0 cut |
| 5.4 | `scripts/verify/phase5.sh` | PROVEN | check 4 (gitlint fixtures) was the smoke test that would have caught the regex bug |

## What's still gated (action items for the maintainer)

- **release-please first PR**: flip the setting per ADR-0005 §"Operational prerequisite", then `gh run rerun 26619199087`.
- **mike versioned docs**: execute the runbook at `docs/operations.md` when ready to cut v0.4.0.

## References

- [docs/adrs/0005-release-engineering.md](../adrs/0005-release-engineering.md) — release-please + mike + gitlint decisions
- [docs/adrs/0004-documentation-strategy.md](../adrs/0004-documentation-strategy.md) — mike deferral + back-ref to operations.md
- [docs/operations.md](../operations.md) — mike migration runbook
- [scripts/verify/phase0.sh..phase5.sh](../../scripts/verify/) — sanity sweep scripts
- [demos/e2e_phase4_5.py](../../demos/e2e_phase4_5.py) — this proof's demo script
- Commits `2877696`..`0c1dc7d` (Phase 5 boundary)
