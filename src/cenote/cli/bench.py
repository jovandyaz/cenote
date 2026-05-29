# SPDX-License-Identifier: Apache-2.0
"""`cenote bench miracl-es` — run the MIRACL-es retrieval benchmark."""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import typer

from cenote.bench.metrics import RunDict, evaluate_run
from cenote.bench.miracl import FIXTURE_CORPUS, FIXTURE_QUERIES, MiraclLoader
from cenote.bench.report import generate_markdown_report
from cenote.bench.runner import BenchRunner
from cenote.embedders.base import Embedder
from cenote.embedders.cohere import CohereEmbedder
from cenote.embedders.mock import MockEmbedder
from cenote.stores.base import VectorStore
from cenote.stores.memory import InMemoryVectorStore
from cenote.tokenizers.spanish import SpanishTokenizer

bench_app = typer.Typer(no_args_is_help=True)


@bench_app.command("miracl-es")
def miracl_es(
    retrievers: str = typer.Option(
        "bm25,vector,hybrid",
        help="Comma-separated list: any of bm25,vector,hybrid",
    ),
    top_k: int = typer.Option(1000, help="Top-k retrieved per query"),
    rrf_k: int = typer.Option(60, help="RRF k parameter for hybrid"),
    split: str = typer.Option("dev", help="MIRACL split: dev or train"),
    dry_run: bool = typer.Option(False, help="Use bundled fixture, no network"),
    output: Path | None = typer.Option(None, help="Write markdown report to PATH"),
    hf_token: str | None = typer.Option(None, envvar="HF_TOKEN"),
    cohere_key: str | None = typer.Option(None, envvar="COHERE_API_KEY"),
) -> None:
    """Run the MIRACL-es retrieval benchmark and print per-retriever metrics."""
    try:
        names = [n.strip() for n in retrievers.split(",") if n.strip()]
        per_retriever = asyncio.run(
            _run_benchmark(
                retriever_names=names,
                top_k=top_k,
                rrf_k=rrf_k,
                split=split,
                dry_run=dry_run,
                hf_token=hf_token,
                cohere_key=cohere_key,
            )
        )
    except Exception as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _print_table(per_retriever)
    if output is not None:
        embedder_id = "mock:default" if dry_run else "cohere:embed-multilingual-v3.0"
        dataset_label = f"MIRACL-{'es' if not dry_run else 'es (dry-run fixture)'} {split}"
        markdown = generate_markdown_report(
            metrics=per_retriever,
            dataset=dataset_label,
            embedder=embedder_id,
            commit=_git_commit_short(),
            generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
        typer.echo(f"\nReport written to {output}")


async def _run_benchmark(
    *,
    retriever_names: list[str],
    top_k: int,
    rrf_k: int,
    split: str,
    dry_run: bool,
    hf_token: str | None,
    cohere_key: str | None,
) -> dict[str, dict[str, float]]:
    """Build loader once, index, run retrievers, load qrels, and evaluate."""
    loader, embedder, store = _build_components(
        split=split, dry_run=dry_run, hf_token=hf_token, cohere_key=cohere_key
    )
    runner = BenchRunner(
        loader=loader,
        embedder=embedder,
        store=store,
        tokenizer=SpanishTokenizer(),
    )
    await runner.index()
    runs: dict[str, RunDict] = await runner.run_all(
        retrievers=retriever_names, top_k=top_k, rrf_k=rrf_k
    )
    qrels = await loader.load_qrels()
    return {name: evaluate_run(qrels, run) for name, run in runs.items()}


def _build_components(
    *, split: str, dry_run: bool, hf_token: str | None, cohere_key: str | None
) -> tuple[MiraclLoader, Embedder, VectorStore]:
    if dry_run:
        loader = MiraclLoader.from_fixture(corpus_path=FIXTURE_CORPUS, queries_path=FIXTURE_QUERIES)
        embedder: Embedder = MockEmbedder(dimensions=128)
        store: VectorStore = InMemoryVectorStore(dimensions=128)
        return loader, embedder, store

    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError(
            "HF_TOKEN is required for the real MIRACL-es dataset (gated). "
            "Pass --hf-token, set HF_TOKEN, or use --dry-run."
        )
    api_key = cohere_key or os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise ValueError(
            "COHERE_API_KEY is required to embed the MIRACL-es corpus. "
            "Pass --cohere-key, set COHERE_API_KEY, or use --dry-run."
        )
    loader = MiraclLoader.from_huggingface(split=split, hf_token=token)
    real_embedder = CohereEmbedder(api_key=api_key)
    real_store = InMemoryVectorStore(dimensions=real_embedder.dimensions)
    return loader, real_embedder, real_store


def _print_table(per_retriever: dict[str, dict[str, float]]) -> None:
    typer.echo(f"{'Retriever':<10}  {'nDCG@10':>8}  {'Recall@100':>11}  {'Recall@1000':>12}")
    typer.echo("-" * 47)
    for name, scores in per_retriever.items():
        typer.echo(
            f"{name:<10}  {scores['ndcg@10']:>8.4f}  "
            f"{scores['recall@100']:>11.4f}  {scores['recall@1000']:>12.4f}"
        )


def _git_commit_short() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 — PATH-resolved git
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"
