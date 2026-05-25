"""Tests for cenote.eval.metrics — BEIR-style retrieval quality measures."""

from __future__ import annotations

import hashlib

import pytest

from cenote.errors import ConfigurationError
from cenote.eval.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k
from cenote.models import Chunk, RetrievalResult


def _result(content: str, *, idx: int, score: float) -> RetrievalResult:
    chunk = Chunk(
        id=f"d:{idx}",
        document_id="d",
        content=content,
        position=idx,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    return RetrievalResult(chunk=chunk, score=score, retriever="vector")


class TestPrecisionAtK:
    def test_perfect_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:1", "d:2", "d:3", "d:4"}
        assert precision_at_k(results, relevant, k=5) == pytest.approx(1.0)

    def test_zero_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant: set[str] = set()
        assert precision_at_k(results, relevant, k=5) == 0.0

    def test_partial_precision(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:2"}  # 2 of top-5 are relevant
        assert precision_at_k(results, relevant, k=5) == pytest.approx(0.4)

    def test_k_larger_than_results(self) -> None:
        results = [_result("r0", idx=0, score=1.0)]
        assert precision_at_k(results, {"d:0"}, k=10) == pytest.approx(1.0)

    def test_k_must_be_positive(self) -> None:
        with pytest.raises(ConfigurationError):
            precision_at_k([], set(), k=0)

    def test_empty_results_returns_zero(self) -> None:
        assert precision_at_k([], {"d:0"}, k=5) == 0.0


class TestRecallAtK:
    def test_all_relevant_found(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        relevant = {"d:0", "d:1"}
        assert recall_at_k(results, relevant, k=5) == pytest.approx(1.0)

    def test_partial_recall(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(3)]
        relevant = {"d:0", "d:99"}  # 1 of 2 found in top-3
        assert recall_at_k(results, relevant, k=3) == pytest.approx(0.5)

    def test_empty_relevant_returns_zero(self) -> None:
        results = [_result("r0", idx=0, score=1.0)]
        assert recall_at_k(results, set(), k=1) == 0.0

    def test_k_must_be_positive(self) -> None:
        with pytest.raises(ConfigurationError):
            recall_at_k([], set(), k=0)


class TestMeanReciprocalRank:
    def test_first_rank(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        assert mean_reciprocal_rank(results, {"d:0"}) == pytest.approx(1.0)

    def test_third_rank(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(5)]
        assert mean_reciprocal_rank(results, {"d:2"}) == pytest.approx(1.0 / 3.0)

    def test_no_relevant_in_results_returns_zero(self) -> None:
        results = [_result(f"r{i}", idx=i, score=1.0 - 0.1 * i) for i in range(3)]
        assert mean_reciprocal_rank(results, {"d:99"}) == 0.0
