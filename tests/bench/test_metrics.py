# SPDX-License-Identifier: Apache-2.0
"""Tests for cenote.bench.metrics — nDCG@10, Recall@k, and RRF fusion."""

from __future__ import annotations

import math

import pytest

from cenote.bench.metrics import evaluate_run, rrf_fuse


class TestEvaluateRun:
    def test_ndcg_perfect_ranking_is_one(self) -> None:
        qrels = {"q1": {"d1": 1, "d2": 1, "d3": 1}}
        run = {"q1": {"d1": 3.0, "d2": 2.0, "d3": 1.0, "d4": 0.5}}
        scores = evaluate_run(qrels, run, metrics=["ndcg@10"])
        assert scores["ndcg@10"] == pytest.approx(1.0)

    def test_recall_at_100_full_match_is_one(self) -> None:
        qrels = {"q1": {"d1": 1, "d2": 1}}
        run = {"q1": {"d1": 1.0, "d2": 0.5, "d3": 0.1}}
        scores = evaluate_run(qrels, run, metrics=["recall@100"])
        assert scores["recall@100"] == pytest.approx(1.0)

    def test_recall_at_100_partial(self) -> None:
        qrels = {"q1": {"d1": 1, "d2": 1, "d3": 1, "d4": 1, "d5": 1}}
        run = {"q1": {"d1": 5.0, "d2": 4.0, "d3": 3.0, "d99": 2.0, "d100": 1.0}}
        scores = evaluate_run(qrels, run, metrics=["recall@100"])
        assert scores["recall@100"] == pytest.approx(0.6)

    def test_default_metrics_returns_three_keys(self) -> None:
        qrels = {"q1": {"d1": 1}}
        run = {"q1": {"d1": 1.0}}
        scores = evaluate_run(qrels, run)
        assert set(scores.keys()) == {"ndcg@10", "recall@100", "recall@1000"}

    def test_averages_across_queries(self) -> None:
        qrels = {"q1": {"d1": 1}, "q2": {"d2": 1}}
        run = {
            "q1": {"d1": 1.0},
            "q2": {"d_wrong": 1.0},
        }
        scores = evaluate_run(qrels, run, metrics=["ndcg@10"])
        assert scores["ndcg@10"] == pytest.approx(0.5)


class TestRRFFuse:
    def test_rrf_two_runs_with_shared_doc_ranks_it_first(self) -> None:
        run_a = {"q1": {"d1": 1.0, "d2": 0.9}}
        run_b = {"q1": {"d2": 1.0, "d3": 0.9}}
        fused = rrf_fuse([run_a, run_b], k=60)
        ranking = sorted(fused["q1"].items(), key=lambda kv: kv[1], reverse=True)
        assert ranking[0][0] == "d2"

    def test_rrf_score_matches_cormack_formula(self) -> None:
        """RRF(d) = sum over runs of 1/(k + rank(d)). Cormack et al., SIGIR 2009."""
        run_a = {"q1": {"d1": 5.0, "d2": 4.0}}
        run_b = {"q1": {"d2": 5.0, "d3": 4.0}}
        fused = rrf_fuse([run_a, run_b], k=60)
        expected_d2 = 1.0 / (60 + 2) + 1.0 / (60 + 1)
        expected_d1 = 1.0 / (60 + 1)
        expected_d3 = 1.0 / (60 + 2)
        assert fused["q1"]["d2"] == pytest.approx(expected_d2, abs=1e-9)
        assert fused["q1"]["d1"] == pytest.approx(expected_d1, abs=1e-9)
        assert fused["q1"]["d3"] == pytest.approx(expected_d3, abs=1e-9)

    def test_rrf_single_run_preserves_ordering(self) -> None:
        run = {"q1": {"d1": 3.0, "d2": 2.0, "d3": 1.0}}
        fused = rrf_fuse([run], k=60)
        ranking = sorted(fused["q1"].items(), key=lambda kv: kv[1], reverse=True)
        assert [d for d, _ in ranking] == ["d1", "d2", "d3"]

    def test_rrf_default_k_is_60(self) -> None:
        run_a = {"q1": {"d1": 1.0}}
        run_b = {"q1": {"d2": 1.0}}
        with_default = rrf_fuse([run_a, run_b])
        with_k_60 = rrf_fuse([run_a, run_b], k=60)
        assert with_default == with_k_60

    def test_rrf_empty_runs_returns_empty(self) -> None:
        assert rrf_fuse([{"q1": {}}]) == {"q1": {}}


class TestRanxInterop:
    def test_qrels_run_type_aliases_are_compatible(self) -> None:
        """The QrelsDict / RunDict aliases must match what ranx accepts internally."""
        qrels = {"q1": {"d1": 1}}
        run = {"q1": {"d1": 1.0}}
        scores = evaluate_run(qrels, run, metrics=["ndcg@10"])
        assert math.isfinite(scores["ndcg@10"])
