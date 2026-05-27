# SPDX-License-Identifier: Apache-2.0
"""Tests for the bundled eval-dataset loaders."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from cenote.eval import (
    EvalDataset,
    load_cenote_mini_es,
    load_miracl_en_subset,
    load_miracl_es_subset,
)


class TestEvalDatasetLoaders:
    def test_load_cenote_mini_es_smoke(self) -> None:
        ds = load_cenote_mini_es()
        assert isinstance(ds, EvalDataset)
        assert ds.language == "es"
        assert len(ds.documents) >= 10
        assert len(ds.queries) >= 5
        doc_ids = {d.id for d in ds.documents}
        for q in ds.queries:
            assert any(rid in doc_ids for rid in q.relevant_doc_ids), q.id

    def test_cenote_mini_es_contains_spanish_content(self) -> None:
        ds = load_cenote_mini_es()
        text_blob = " ".join(d.content for d in ds.documents).lower()
        assert any(stop in text_blob for stop in (" el ", " la ", " de ", " que ", " del "))
        assert any(accent in text_blob for accent in "áéíóúñ")

    def test_qrels_derived_from_queries(self) -> None:
        ds = load_cenote_mini_es()
        for query in ds.queries:
            assert ds.qrels[query.id] == set(query.relevant_doc_ids)

    @pytest.mark.parametrize(
        "loader,expected_lang",
        [(load_miracl_es_subset, "es"), (load_miracl_en_subset, "en")],
    )
    def test_load_miracl_subsets(
        self, loader: Callable[[], EvalDataset], expected_lang: str
    ) -> None:
        ds = loader()
        assert ds.language == expected_lang
        if not ds.documents:
            pytest.skip(f"MIRACL {expected_lang} subset is empty (build deferred)")
        assert len(ds.documents) > 0
        assert len(ds.queries) > 0
