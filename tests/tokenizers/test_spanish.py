# SPDX-License-Identifier: Apache-2.0
"""Tests for SpanishTokenizer."""

from __future__ import annotations

from cenote.tokenizers import SpanishTokenizer, Tokenizer


class TestSpanishTokenizer:
    def test_implements_protocol(self) -> None:
        tok: Tokenizer = SpanishTokenizer()
        assert hasattr(tok, "tokenize")

    def test_stems_verbs(self) -> None:
        tok = SpanishTokenizer()
        a = tok.tokenize("corriendo")
        b = tok.tokenize("corremos")
        assert a == b
        assert len(a) == 1

    def test_drops_stopwords(self) -> None:
        tok = SpanishTokenizer()
        out = tok.tokenize("el perro la casa de")
        assert "el" not in out
        assert "la" not in out
        assert "de" not in out
        assert len(out) == 2

    def test_strip_accents_changes_output(self) -> None:
        folded = SpanishTokenizer(strip_accents=True).tokenize("niño café")
        unfolded = SpanishTokenizer(strip_accents=False).tokenize("niño café")
        assert folded != unfolded
        assert all("ñ" not in t and "é" not in t for t in folded)
        assert any("ñ" in t or "é" in t for t in unfolded)

    def test_lowercase_default(self) -> None:
        tok = SpanishTokenizer()
        upper = tok.tokenize("MADRID")
        lower = tok.tokenize("madrid")
        assert upper == lower

    def test_idempotent_double_tokenize(self) -> None:
        tok = SpanishTokenizer()
        once = tok.tokenize("perros corriendo")
        twice = tok.tokenize(" ".join(once))
        assert once == twice

    def test_ascii_english_degrades_gracefully(self) -> None:
        tok = SpanishTokenizer()
        out = tok.tokenize("running dogs in the park")
        assert len(out) >= 2
        assert all(isinstance(t, str) for t in out)

    def test_empty_string(self) -> None:
        assert SpanishTokenizer().tokenize("") == []

    def test_punctuation_only(self) -> None:
        assert SpanishTokenizer().tokenize("!!!,...???") == []
