# SPDX-License-Identifier: Apache-2.0
"""Tests for cenote.bench.report — Pyserini-2cr-style markdown generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cenote.bench.report import generate_markdown_report
from cenote.cli import app


@pytest.fixture
def sample_metrics() -> dict[str, dict[str, float]]:
    return {
        "bm25": {"ndcg@10": 0.319, "recall@100": 0.726, "recall@1000": 0.882},
        "vector": {"ndcg@10": 0.585, "recall@100": 0.842, "recall@1000": 0.937},
        "hybrid": {"ndcg@10": 0.627, "recall@100": 0.871, "recall@1000": 0.952},
    }


class TestGenerateMarkdownReport:
    def test_contains_dataset_label(self, sample_metrics: dict[str, dict[str, float]]) -> None:
        md = generate_markdown_report(
            metrics=sample_metrics,
            dataset="MIRACL-es dev",
            embedder="cohere:embed-multilingual-v3.0",
            commit="abc1234",
            generated_at="2026-05-30",
        )
        assert "MIRACL-es dev" in md

    def test_contains_all_retriever_rows(self, sample_metrics: dict[str, dict[str, float]]) -> None:
        md = generate_markdown_report(
            metrics=sample_metrics,
            dataset="MIRACL-es dev",
            embedder="cohere:embed-multilingual-v3.0",
            commit="abc1234",
            generated_at="2026-05-30",
        )
        assert "BM25" in md
        assert "Vector" in md
        assert "Hybrid" in md

    def test_metric_values_formatted_to_four_decimals(
        self, sample_metrics: dict[str, dict[str, float]]
    ) -> None:
        md = generate_markdown_report(
            metrics=sample_metrics,
            dataset="MIRACL-es dev",
            embedder="cohere:embed-multilingual-v3.0",
            commit="abc1234",
            generated_at="2026-05-30",
        )
        assert "0.3190" in md
        assert "0.6270" in md

    def test_includes_provenance_fields(self, sample_metrics: dict[str, dict[str, float]]) -> None:
        md = generate_markdown_report(
            metrics=sample_metrics,
            dataset="MIRACL-es dev",
            embedder="cohere:embed-multilingual-v3.0",
            commit="abc1234",
            generated_at="2026-05-30",
        )
        assert "cohere:embed-multilingual-v3.0" in md
        assert "abc1234" in md
        assert "2026-05-30" in md

    def test_includes_reproducibility_command(
        self, sample_metrics: dict[str, dict[str, float]]
    ) -> None:
        md = generate_markdown_report(
            metrics=sample_metrics,
            dataset="MIRACL-es dev",
            embedder="cohere:embed-multilingual-v3.0",
            commit="abc1234",
            generated_at="2026-05-30",
        )
        assert "cenote bench miracl-es" in md

    def test_is_deterministic_for_same_inputs(
        self, sample_metrics: dict[str, dict[str, float]]
    ) -> None:
        kwargs = {
            "metrics": sample_metrics,
            "dataset": "MIRACL-es dev",
            "embedder": "cohere:embed-multilingual-v3.0",
            "commit": "abc1234",
            "generated_at": "2026-05-30",
        }
        assert generate_markdown_report(**kwargs) == generate_markdown_report(**kwargs)


class TestCliOutputFlag:
    def test_dry_run_writes_output_file(self, tmp_path: Path) -> None:
        out = tmp_path / "benchmarks.md"
        runner = CliRunner()
        result = runner.invoke(app, ["bench", "miracl-es", "--dry-run", "--output", str(out)])
        assert result.exit_code == 0, result.output
        assert out.is_file()
        content = out.read_text()
        assert "BM25" in content
        assert "Vector" in content
        assert "Hybrid" in content
