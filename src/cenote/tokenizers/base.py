# SPDX-License-Identifier: Apache-2.0
"""Tokenizer Protocol — language-agnostic token producer for BM25 retrievers."""

from __future__ import annotations

from typing import Protocol


class Tokenizer(Protocol):
    """Maps a query or document string to a list of normalized tokens."""

    def tokenize(self, text: str) -> list[str]:
        """Return the tokens (stems, lowercase, stopwords removed) for `text`."""
        ...
