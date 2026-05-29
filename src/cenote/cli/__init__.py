# SPDX-License-Identifier: Apache-2.0
"""cenote Typer CLI — `cenote bench miracl-es [...]`."""

from __future__ import annotations

import typer

from cenote.cli.bench import bench_app

app = typer.Typer(
    name="cenote",
    no_args_is_help=True,
    help="cenote — Spanish-first retrieval framework. Subcommands listed below.",
)
app.add_typer(bench_app, name="bench", help="Run public retrieval benchmarks.")

__all__ = ["app"]
