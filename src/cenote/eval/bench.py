# SPDX-License-Identifier: Apache-2.0
"""RetrievalBenchmark — runs a Retriever against an EvalDataset, computes metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cenote.eval.datasets import EvalDataset
from cenote.eval.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k
from cenote.models import RetrievalResult
from cenote.retrievers.base import Retriever

logger = logging.getLogger(__name__)


def _doc_id_of(r: RetrievalResult) -> str:
    return r.chunk.document_id


@dataclass(frozen=True)
class BenchmarkResult:
    dataset: str
    retriever_label: str
    k: int
    precision_at_k: float
    recall_at_k: float
    mrr: float
    per_query: dict[str, dict[str, float]] = field(default_factory=dict)


class RetrievalBenchmark:
    """Runs a Retriever over an EvalDataset and reports aggregated metrics.

    `precision@k`, `recall@k`, `MRR` are computed using `cenote.eval.metrics`.
    Designed to wrap any object implementing the `Retriever` Protocol — vector,
    BM25, hybrid, or hybrid+rerank pipelines. Compares retrieval results to
    qrels at the document level (`chunk.document_id`), matching how qrels are
    authored.

    `precision_at_k` here is `hits / len(top)` (precision-among-returned), not
    strict BEIR `hits / k`. The two converge when the retriever always
    returns >= k results per query.
    """

    def __init__(self, retriever: Retriever, namespace: str = "default") -> None:
        self._retriever = retriever
        self._namespace = namespace

    async def run(self, dataset: EvalDataset, k: int = 10) -> BenchmarkResult:
        per_query: dict[str, dict[str, float]] = {}
        p_sum = 0.0
        r_sum = 0.0
        mrr_sum = 0.0
        for query in dataset.queries:
            results = await self._retriever.retrieve(query.text, namespace=self._namespace, limit=k)
            relevant = dataset.qrels.get(query.id, set())
            p = precision_at_k(results, relevant, k, key=_doc_id_of)
            r = recall_at_k(results, relevant, k, key=_doc_id_of)
            mrr = mean_reciprocal_rank(results, relevant, key=_doc_id_of)
            per_query[query.id] = {"precision_at_k": p, "recall_at_k": r, "mrr": mrr}
            p_sum += p
            r_sum += r
            mrr_sum += mrr
        n = max(len(dataset.queries), 1)
        return BenchmarkResult(
            dataset=dataset.name,
            retriever_label=_label_for(self._retriever),
            k=k,
            precision_at_k=p_sum / n,
            recall_at_k=r_sum / n,
            mrr=mrr_sum / n,
            per_query=per_query,
        )


def _label_for(retriever: Retriever) -> str:
    cls = type(retriever).__name__
    model_id: str | None = getattr(retriever, "model_id", None)
    return f"{cls}(model={model_id})" if model_id else cls
