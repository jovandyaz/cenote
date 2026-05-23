"""Protocol shape only — no concrete reranker exists in M1.0."""

from __future__ import annotations

from cenote.rerankers import Reranker


def test_reranker_protocol_is_importable() -> None:
    assert Reranker is not None
