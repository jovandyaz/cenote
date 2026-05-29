# Retrieval benchmarks

cenote-core publishes reproducible retrieval numbers using the
[Pyserini-2cr](https://castorini.github.io/pyserini/2cr/miracl.html) table format.
Methodology, caveats, and discarded benchmarks are documented in
[ADR-0009](adrs/0009-miracl-es-benchmark.md).

## MIRACL-es (dev split, 648 queries, ~10.4M passages)

> **Status: pending Phase F.** The full corpus embed pass is queued behind explicit
> budget approval (~$80–125 USD one-shot Cohere cost). The bench infra ships in
> v0.5.0 — only the headline numbers are pending. See ADR-0009 §Implementation notes.

Methodology: TREC-format runs evaluated with [ranx](https://github.com/AmenRa/ranx).
Reproducible via:

```bash
uv run cenote bench miracl-es --output docs/benchmarks.md
```

| Retriever        | nDCG@10 | Recall@100 | Recall@1000 |
|------------------|--------:|-----------:|------------:|
| BM25             | _pending_ | _pending_ | _pending_ |
| Vector (cohere:embed-multilingual-v3.0) | _pending_ | _pending_ | _pending_ |
| Hybrid (RRF, k=60) | _pending_ | _pending_ | _pending_ |

**Provenance** — embedder: `cohere:embed-multilingual-v3.0` · generated: _pending_ · cost: _pending_

### Reference baselines (for context only — not cenote results)

- [Pyserini-2cr MIRACL-es](https://castorini.github.io/pyserini/2cr/miracl.html): BM25-only ≈ 0.319 nDCG@10; BM25 + mDPR (fine-tuned on MIRACL train) ≈ 0.641 nDCG@10.
- [Cohere multilingual-v3 announcement](https://cohere.com/blog/embedding-v3): dense-only on MIRACL-es ≈ 0.58 nDCG@10.

Direct row-for-row comparison to Pyserini is misleading: their mDPR is fine-tuned on MIRACL train, ours is a generic multilingual embedder.

## Smoke test (always available — no network, no API spend)

```bash
uv run cenote bench miracl-es --dry-run
```

Runs the full pipeline against a 10-passage / 3-query bundled fixture under
`src/cenote/bench/fixtures/`. Useful for CI regression detection and for
contributors verifying their setup before the real run.

## Discarded benchmarks

A deep survey of MTEB full, BEIR full, Mr. TyDi, ARES, and TruLens is in
[ADR-0009](adrs/0009-miracl-es-benchmark.md#context). Short version: most measure
the embedder model (not cenote's wiring) or have no Spanish coverage.
