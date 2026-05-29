# SPDX-License-Identifier: Apache-2.0
"""Tests for the `cenote bench miracl-es` Typer CLI."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cenote.cli import app


@pytest.fixture
def cli() -> CliRunner:
    return CliRunner()


class TestBenchMiraclEsCli:
    def test_dry_run_exits_zero(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["bench", "miracl-es", "--dry-run"])
        assert result.exit_code == 0, result.output

    def test_dry_run_prints_three_metric_rows(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["bench", "miracl-es", "--dry-run"])
        assert result.exit_code == 0
        assert "bm25" in result.output.lower()
        assert "vector" in result.output.lower()
        assert "hybrid" in result.output.lower()

    def test_dry_run_prints_default_metrics(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["bench", "miracl-es", "--dry-run"])
        out = result.output.lower()
        assert "ndcg" in out
        assert "recall" in out

    def test_dry_run_single_retriever(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["bench", "miracl-es", "--dry-run", "--retrievers", "bm25"])
        assert result.exit_code == 0
        assert "bm25" in result.output.lower()

    def test_real_mode_without_hf_token_exits_nonzero(self, cli: CliRunner) -> None:
        result = cli.invoke(
            app,
            ["bench", "miracl-es", "--retrievers", "bm25"],
            env={"HF_TOKEN": "", "COHERE_API_KEY": ""},
        )
        assert result.exit_code != 0

    def test_unknown_retriever_exits_nonzero(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["bench", "miracl-es", "--dry-run", "--retrievers", "garbage"])
        assert result.exit_code != 0
