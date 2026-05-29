# ADR-0009 — MIRACL-es retrieval benchmark as the public quality signal

**Status**: Accepted (infra shipped in v0.5.0; numbers pending Phase F)
**Date**: 2026-05-29
**Deciders**: Jovan Díaz

## Context

Through M1.0–M1.2 cenote-core validated correctness via unit tests and one informal end-to-end smoke test against `knowtis-cenote-demo` (39 Spanish notes, 5 queries). That demo proved the stack *runs* under production-like conditions; it did not produce a publishable, reproducible number that lets external readers compare cenote-core to other retrieval libraries.

The framing question is: what benchmark *means* something for a Spanish-first retrieval library, and what *doesn't*?

Surveyed candidates (full reasoning in [docs/proofs/v0.5.0-bench-discards.md](../proofs/v0.5.0-bench-discards.md) — TODO):

| Benchmark | Verdict for cenote-core | Reason |
|---|---|---|
| **MIRACL-es dev** (648 queries, ~10.4M passages) | **adopt** | Only candidate that ejercita the full stack end-to-end on native Spanish corpus with public baselines (Pyserini, Cohere, mE5) |
| BEIR SciFact / NFCorpus | adopt later (M1.3) | Useful sanity check for non-regression of English capability; English-only |
| MTEB full | reject | Mostly classification/STS; measures embedder, not cenote |
| MTEB Spanish retrieval slice | defer to v0.6+ | Useful when we have a cenote-owned embedder impl to evaluate |
| Mr. TyDi | reject | Superseded by MIRACL (same authors, larger Spanish corpus) |
| ARES | reject | RAG end-to-end framework; requires `agents/` (M2.0+) |
| TruLens | reject | Redundant with DeepEval already in stack |

## Decision

Adopt **MIRACL-es dev** as cenote-core's primary public quality signal, reported in the **Pyserini-2cr** table format and published at `docs/benchmarks.md`. Surface a single headline number (Hybrid-RRF nDCG@10) on the README. Wire reproducibility through a public CLI: `uv run cenote bench miracl-es`.

### Three rows, one table

| Retriever | Implementation | Cost driver |
|---|---|---|
| **BM25** | `cenote.tokenizers.SpanishTokenizer` + `cenote.retrievers.BM25Retriever` | $0 — lexical only |
| **Vector** | `cenote.embedders.CohereEmbedder` (multilingual-v3) + `cenote.retrievers.VectorRetriever` | one-shot Cohere embedding of 10.4M passages |
| **Hybrid (RRF)** | `cenote.bench.metrics.rrf_fuse` with `k=60` over BM25 + Vector runs | depends on Vector |

The Hybrid → BM25 delta is the cenote-core thesis made measurable. If RRF fusion of Spanish-stemmed BM25 with multilingual dense embeddings adds nothing on a public benchmark, our positioning ("Spanish-first hybrid retrieval") collapses. If it adds the expected ~+0.30 nDCG@10, the README badge is defensible.

### Stack decisions

- **Eval lib**: [ranx](https://github.com/AmenRa/ranx) — pure-Python, TREC-format compatible, native RRF, ~5× less LOC than `pytrec_eval` for our use case, no macOS arm64 C-extension friction.
- **Vector store**: `cenote.stores.InMemoryVectorStore` for the benchmark itself (corpus fits comfortably in RAM once embedded). PgVector remains the production store; using InMemory here removes infra setup from the reproducibility path.
- **Embedder**: Cohere `embed-multilingual-v3.0` is the v0.5.0 baseline. Voyage `voyage-multilingual-2` may be added later for direct comparison once we settle the embedder default question (per ADR-0006 deferral).
- **Auth**: `HF_TOKEN` env var (MIRACL is a gated HF dataset; user must accept terms once at https://huggingface.co/datasets/miracl/miracl). `COHERE_API_KEY` env var. CLI fails early on missing tokens with actionable messages.
- **Bench fixture bundle**: a 10-passage / 3-query JSONL fixture ships at `src/cenote/bench/fixtures/` so `cenote bench miracl-es --dry-run` works without network. CI uses this; users use it for smoke testing before committing to the real embed pass.

### Code surface

Six new public symbols, all under `cenote.bench`:

- `MiraclLoader` (`from_fixture` / `from_huggingface` constructors)
- `evaluate_run(qrels, run, metrics) -> dict[str, float]`
- `rrf_fuse(runs, k=60) -> RunDict`
- `BenchRunner` (orchestrates BM25 + Vector + Hybrid over an indexed corpus)
- `generate_markdown_report(...)` (deterministic Pyserini-2cr-style table)
- CLI: `cenote bench miracl-es [--dry-run] [--retrievers ...] [--output PATH] ...`

50 new unit tests in `tests/bench/`, all green; `mypy --strict` clean; `ruff` clean. Phase F (real run against full corpus) is **deferred from v0.5.0 to a later release** pending budget approval — see Implementation notes.

### Documentation pattern

- `docs/benchmarks.md` — canonical table, Pyserini-2cr format, with provenance line (embedder + commit SHA + date).
- README badge linking to `docs/benchmarks.md` (added once Phase F populates real numbers).
- ADR per benchmark adopted (this one is the first; one per new dataset as the suite grows).

## Alternatives considered

**Inventar un benchmark más barato** (e.g., XQUAD-es subset, ~1K passages). Rejected: no one recognizes it, no baselines exist, defeats the public-credibility goal. Smoke-testing on knowtis already covers the "does it work on real data" question.

**Sampled MIRACL-es** (e.g., 100K passages instead of 10.4M). Rejected: breaks comparability with Pyserini / mMARCO / BGE-M3 baselines that all report on FULL dev. Sampling would degrade to "smoke test with metrics" — a strictly worse position than either smoke testing or the real benchmark.

**Vendor-managed eval** (Cohere coral leaderboard, Voyage internal benchmarks). Rejected: those measure their embedders, not cenote's wiring.

## Consequences

**Positive**:
- One reproducible number for the README — replaces hand-wavy "Spanish-first" positioning with a defended claim.
- CI smoke test guard against pipeline regressions via `--dry-run` (fixture-based, no network).
- Bench infra (loader, metrics, runner, report) is reusable — adding BEIR or MTEB later is a new dataset wrapper, not a new framework.
- Establishes the publish-a-benchmark muscle for the project; every retrieval-touching release going forward can re-run and update the table.

**Negative**:
- New runtime dep surface for users who want to reproduce: `ranx`, `typer`, `huggingface_hub`. Mitigation: these are needed only to *reproduce*; library consumers (`from cenote import ...`) don't pull them transitively because they live behind the `cenote.bench` / `cenote.cli` import paths and are declared in dev deps. (Future: move to `[bench]` optional extra when v0.6 surface stabilizes.)
- Cohere cost (~$80–125 one-shot for the corpus pass) couples the public number to a paid API. Mitigation: cached parquet of embeddings + reproducibility script means re-runs are free for anyone with the artifact; the *first* embed pass is the only paid step.
- MIRACL leaderboard contamination (mDPR was fine-tuned on MIRACL train) means our Hybrid score is not directly comparable to Pyserini's 0.641 reference — embedder must be labeled explicitly in the table.

**Neutral**:
- Future benchmarks (BEIR sanity check, MTEB ES slice, end-to-end RAG eval) will land as separate ADRs and table rows. This ADR sets the pattern.

## Implementation notes

### 2026-05-29 — Phase A–E shipped in v0.5.0

Wire-up complete: loader + metrics + RRF + runner + CLI + report generator, 50 unit tests verde, mypy strict + ruff clean, CLI E2E via `cenote bench miracl-es --dry-run`. Committed as `feat(bench): MIRACL-es harness with ranx metrics and Pyserini-2cr report`. release-please correctly bumped 0.4.1 → 0.5.0 (minor bump per semver: new public module + new top-level CLI).

### Phase F deferred (budget gate)

The real corpus embed pass is **gated on explicit budget approval** for the ~$80–125 Cohere cost. The CLI works against the bundled fixture today (`--dry-run`); the path to filling in real numbers is a single command (`cenote bench miracl-es --output docs/benchmarks.md`) once the budget green-lights.

### Phase F open checklist (to execute when budget approved)

- [ ] Accept MIRACL terms at https://huggingface.co/datasets/miracl/miracl with the maintainer's HF account.
- [ ] Provision `HF_TOKEN` and `COHERE_API_KEY` in the shell.
- [ ] Run `uv run cenote bench miracl-es --output docs/benchmarks.md`.
- [ ] Verify the resulting table has three populated rows (BM25 / Vector / Hybrid).
- [ ] Cache the embeddings parquet under `.cache/cenote/miracl-es/` for free re-runs.
- [ ] Add README badge with the Hybrid nDCG@10 number.
- [ ] Write `docs/proofs/v0.X-miracl-es.md` ship report including the actual Cohere cost.
- [ ] Commit + push; release-please bumps to the next minor or patch as appropriate.

## References

- [MIRACL paper](https://arxiv.org/abs/2210.09984) — Zhang et al., 2022. Multilingual IR across 18 languages.
- [Pyserini 2cr — MIRACL](https://castorini.github.io/pyserini/2cr/miracl.html) — the table format we copy.
- [ranx](https://github.com/AmenRa/ranx) — eval library.
- [Cohere embed-multilingual-v3](https://cohere.com/blog/embedding-v3) — embedder choice rationale.
- [Cormack et al., SIGIR 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — RRF formula.
- ADR-0006 (dependency selection) — `ranx` + `typer` + `huggingface_hub` justified against the gate.
- ADR-0008 (monorepo strategy) — future home of `packages/cenote-bench/` if extracted.
