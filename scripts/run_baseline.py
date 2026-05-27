# SPDX-License-Identifier: Apache-2.0
"""Reproducible baseline runner — emits the numbers in docs/benchmarks/...md.

Run with:
    VOYAGE_API_KEY=... COHERE_API_KEY=... \
        uv run python -m scripts.run_baseline > docs/benchmarks/raw-results.json

Skips datasets without documents (MIRACL placeholders) so the runner is usable
even when only `cenote_mini_es` is populated.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Callable
from typing import Any

from cenote.embedders.voyage import VoyageEmbedder
from cenote.eval import (
    EvalDataset,
    RetrievalBenchmark,
    load_cenote_mini_es,
    load_miracl_en_subset,
    load_miracl_es_subset,
)
from cenote.models import Chunk, RetrievalResult
from cenote.rerankers import CohereReranker, VoyageReranker
from cenote.rerankers.base import Reranker
from cenote.retrievers import BM25Retriever, HybridRetriever, VectorRetriever
from cenote.retrievers.base import Retriever
from cenote.stores import InMemoryVectorStore
from cenote.tokenizers import SpanishTokenizer

RERANK_CANDIDATE_POOL = 50


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Missing {name}. Run with:\n"
            f"  VOYAGE_API_KEY=... COHERE_API_KEY=... uv run python -m scripts.run_baseline"
        )
    return value


class _RerankPipeline:
    """Wraps a base Retriever + a Reranker as a Retriever-Protocol composite."""

    def __init__(
        self,
        base: Retriever,
        reranker: Reranker,
        candidate_pool: int = RERANK_CANDIDATE_POOL,
    ) -> None:
        self._base = base
        self._reranker = reranker
        self._candidate_pool = candidate_pool

    async def retrieve(
        self,
        query: str,
        namespace: str,
        limit: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        candidates = await self._base.retrieve(
            query, namespace=namespace, limit=self._candidate_pool, filter=filter
        )
        return await self._reranker.rerank(query, candidates, top_k=limit)


def _chunks_for(ds: EvalDataset) -> list[Chunk]:
    """One Chunk per Document so qrels (doc-level) match bench output 1:1."""
    return [
        Chunk(
            id=d.id,
            document_id=d.id,
            content=d.content,
            position=0,
            content_hash=hashlib.sha256(d.content.encode()).hexdigest(),
        )
        for d in ds.documents
    ]


async def index_and_run(ds: EvalDataset, namespace: str) -> dict[str, dict[str, float]]:
    voyage_key = _require_env("VOYAGE_API_KEY")
    cohere_key = _require_env("COHERE_API_KEY")
    embedder = VoyageEmbedder(api_key=voyage_key)
    store = InMemoryVectorStore(dimensions=embedder.dimensions)
    chunks = _chunks_for(ds)
    embedded = await embedder.embed(chunks)
    await store.upsert(embedded, namespace=namespace)

    vector_r = VectorRetriever(embedder=embedder, store=store)
    bm25_r = BM25Retriever(store=store, tokenizer=SpanishTokenizer())
    hybrid_r = HybridRetriever([vector_r, bm25_r])

    pipelines: list[tuple[str, Retriever]] = [
        ("vector(voyage-3)", vector_r),
        ("bm25(spanish)", bm25_r),
        ("hybrid", hybrid_r),
        ("hybrid+voyage-rerank", _RerankPipeline(hybrid_r, VoyageReranker(api_key=voyage_key))),
        ("hybrid+cohere-rerank", _RerankPipeline(hybrid_r, CohereReranker(api_key=cohere_key))),
    ]
    out: dict[str, dict[str, float]] = {}
    for name, retriever in pipelines:
        bench = RetrievalBenchmark(retriever=retriever, namespace=namespace)
        result = await bench.run(ds, k=10)
        out[name] = {
            "precision_at_10": result.precision_at_k,
            "recall_at_10": result.recall_at_k,
            "mrr": result.mrr,
        }
    return out


async def main() -> None:
    loaders: list[tuple[str, Callable[[], EvalDataset]]] = [
        ("miracl-es-subset", load_miracl_es_subset),
        ("miracl-en-subset", load_miracl_en_subset),
        ("cenote-mini-es", load_cenote_mini_es),
    ]
    all_results: dict[str, dict[str, dict[str, float]]] = {}
    for loader_name, loader in loaders:
        ds = loader()
        if not ds.documents:
            print(f"# Skipping {loader_name}: empty corpus (build deferred)")
            continue
        all_results[loader_name] = await index_and_run(ds, namespace=f"ns-{loader_name}")
    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
