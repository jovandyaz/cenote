# SPDX-License-Identifier: Apache-2.0
"""MIRACL loader — passages, queries, qrels for retrieval benchmarking."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, Literal

from cenote.errors import ConfigurationError
from cenote.models import Chunk

_Mode = Literal["fixture", "huggingface"]

FIXTURE_DIR: Path = Path(__file__).parent / "fixtures"
FIXTURE_CORPUS: Path = FIXTURE_DIR / "miracl_mini_corpus.jsonl"
FIXTURE_QUERIES: Path = FIXTURE_DIR / "miracl_mini_queries.jsonl"


class MiraclLoader:
    """Load MIRACL passages, queries, and qrels for retrieval benchmarking.

    Two source modes:
    - `from_fixture(corpus_path, queries_path)` for unit tests and `--dry-run`.
    - `from_huggingface(hf_token=...)` for the real `miracl/miracl-corpus` +
      `miracl/miracl` gated datasets; requires accepting the terms on HF once
      and supplying an HF access token.
    """

    def __init__(
        self,
        *,
        language: str,
        split: str,
        mode: _Mode,
        fixture_corpus: Path | None = None,
        fixture_queries: Path | None = None,
        hf_token: str | None = None,
    ) -> None:
        self._language = language
        self._split = split
        self._mode = mode
        self._fixture_corpus = fixture_corpus
        self._fixture_queries = fixture_queries
        self._hf_token = hf_token

    @classmethod
    def from_fixture(
        cls,
        corpus_path: Path,
        queries_path: Path,
        *,
        language: str = "es",
        split: str = "dev",
    ) -> MiraclLoader:
        if not corpus_path.is_file():
            raise FileNotFoundError(f"corpus fixture not found: {corpus_path}")
        if not queries_path.is_file():
            raise FileNotFoundError(f"queries fixture not found: {queries_path}")
        return cls(
            language=language,
            split=split,
            mode="fixture",
            fixture_corpus=corpus_path,
            fixture_queries=queries_path,
        )

    @classmethod
    def from_huggingface(
        cls,
        *,
        language: str = "es",
        split: str = "dev",
        hf_token: str | None,
    ) -> MiraclLoader:
        if not hf_token:
            raise ConfigurationError(
                "MIRACL is a gated HF dataset; supply hf_token (env: HF_TOKEN). "
                "Accept terms once at https://huggingface.co/datasets/miracl/miracl"
            )
        return cls(
            language=language,
            split=split,
            mode="huggingface",
            hf_token=hf_token,
        )

    @property
    def namespace(self) -> str:
        return f"miracl-{self._language}"

    async def load_corpus(self) -> AsyncIterator[Chunk]:
        rows = self._iter_corpus_rows()
        for row in rows:
            yield _passage_to_chunk(row, self.namespace)

    async def load_queries(self) -> dict[str, str]:
        return {row["query_id"]: row["query"] for row in self._iter_query_rows()}

    async def load_qrels(self) -> dict[str, dict[str, int]]:
        return {
            row["query_id"]: {p["docid"]: 1 for p in row.get("positive_passages", [])}
            for row in self._iter_query_rows()
        }

    def _iter_corpus_rows(self) -> Iterator[dict[str, Any]]:
        if self._mode == "fixture":
            assert self._fixture_corpus is not None
            yield from _read_jsonl(self._fixture_corpus)
        else:
            yield from _hf_load("miracl/miracl-corpus", self._language, "train", self._hf_token)

    def _iter_query_rows(self) -> Iterator[dict[str, Any]]:
        if self._mode == "fixture":
            assert self._fixture_queries is not None
            yield from _read_jsonl(self._fixture_queries)
        else:
            yield from _hf_load("miracl/miracl", self._language, self._split, self._hf_token)


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                yield json.loads(stripped)


def _hf_load(name: str, language: str, split: str, token: str | None) -> Iterator[dict[str, Any]]:
    from datasets import load_dataset  # type: ignore[import-untyped]

    ds = load_dataset(name, language, split=split, token=token)
    yield from ds


def _passage_to_chunk(row: dict[str, Any], namespace: str) -> Chunk:
    docid = str(row["docid"])
    title = str(row.get("title", "") or "")
    text = str(row["text"])
    content = f"{title}\n\n{text}".strip() if title else text
    return Chunk(
        id=docid,
        document_id=docid,
        content=content,
        position=0,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        metadata={"title": title, "source": namespace},
    )
