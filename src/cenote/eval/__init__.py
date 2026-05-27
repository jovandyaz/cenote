# SPDX-License-Identifier: Apache-2.0
"""Eval primitives — retrieval quality metrics + bundled datasets + bench harness."""

from cenote.eval.bench import BenchmarkResult, RetrievalBenchmark
from cenote.eval.datasets import (
    EvalDataset,
    Query,
    load_cenote_mini_es,
    load_miracl_en_subset,
    load_miracl_es_subset,
)
from cenote.eval.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k

__all__ = [
    "BenchmarkResult",
    "EvalDataset",
    "Query",
    "RetrievalBenchmark",
    "load_cenote_mini_es",
    "load_miracl_en_subset",
    "load_miracl_es_subset",
    "mean_reciprocal_rank",
    "precision_at_k",
    "recall_at_k",
]
