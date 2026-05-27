# SPDX-License-Identifier: Apache-2.0
"""Bundled eval datasets + typed loaders.

JSONL format: first line is a header `{"type":"header", "qrels":[...]}`;
subsequent lines are `{"type":"doc", "id":..., "content":..., "title":...}`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources

from cenote.models import Document


@dataclass(frozen=True)
class Query:
    id: str
    text: str
    relevant_doc_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvalDataset:
    """Eval corpus: queries (with per-query relevant_doc_ids) drive `qrels`.

    `Query.relevant_doc_ids` is the single source of truth for relevance
    judgments. `qrels` is derived once at construction for O(1) lookup.
    """

    name: str
    language: str
    documents: list[Document]
    queries: list[Query]
    qrels: dict[str, set[str]] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "qrels", {q.id: set(q.relevant_doc_ids) for q in self.queries})


def _load_jsonl(filename: str, language: str, name: str) -> EvalDataset:
    docs: list[Document] = []
    queries: list[Query] = []
    with (
        resources.files("cenote.eval.datasets").joinpath(filename).open("r", encoding="utf-8") as fh
    ):
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["type"] == "header":
                for q in row["qrels"]:
                    queries.append(
                        Query(
                            id=q["query_id"],
                            text=q["query"],
                            relevant_doc_ids=tuple(q["relevant_doc_ids"]),
                        )
                    )
            elif row["type"] == "doc":
                docs.append(
                    Document(
                        id=row["id"],
                        content=row["content"],
                        metadata={"title": row.get("title", "")},
                    )
                )
    return EvalDataset(name=name, language=language, documents=docs, queries=queries)


def load_miracl_es_subset() -> EvalDataset:
    """Spanish MIRACL dev subsample (~5000 passages, ~200 queries)."""
    return _load_jsonl("miracl_es_subset.jsonl", "es", "miracl-es-subset")


def load_miracl_en_subset() -> EvalDataset:
    """English MIRACL dev subsample (~5000 passages, ~200 queries)."""
    return _load_jsonl("miracl_en_subset.jsonl", "en", "miracl-en-subset")


def load_cenote_mini_es() -> EvalDataset:
    """Custom ~30 query-doc pairs covering cenote / CFDI / RAG terminology."""
    return _load_jsonl("cenote_mini_es.jsonl", "es", "cenote-mini-es")


__all__ = [
    "EvalDataset",
    "Query",
    "load_cenote_mini_es",
    "load_miracl_en_subset",
    "load_miracl_es_subset",
]
