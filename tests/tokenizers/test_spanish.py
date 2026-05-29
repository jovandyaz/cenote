# SPDX-License-Identifier: Apache-2.0
"""Tests for SpanishTokenizer."""

from __future__ import annotations

import pickle

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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

    def test_pickle_round_trip_default(self) -> None:
        """Tokenizer must survive pickle.dumps/loads — the Stemmer C-ext is not picklable
        but the public behavior must round-trip identically."""
        original = SpanishTokenizer()
        sample = "los perros corriendo en el parque"
        expected = original.tokenize(sample)
        restored = pickle.loads(pickle.dumps(original))  # noqa: S301
        assert isinstance(restored, SpanishTokenizer)
        assert restored.tokenize(sample) == expected

    def test_pickle_round_trip_preserves_strip_accents(self) -> None:
        original = SpanishTokenizer(strip_accents=False)
        sample = "niño café"
        expected = original.tokenize(sample)
        restored = pickle.loads(pickle.dumps(original))  # noqa: S301
        assert restored.tokenize(sample) == expected
        assert restored.tokenize(sample) != SpanishTokenizer(strip_accents=True).tokenize(sample)


@given(
    text=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=500,
    )
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=200)
def test_fold_accents_is_idempotent(text: str) -> None:
    """fold(fold(x)) must equal fold(x) — the operation is a projection."""
    from cenote.tokenizers.spanish import _fold_accents

    folded_once = _fold_accents(text)
    folded_twice = _fold_accents(folded_once)
    assert folded_once == folded_twice


@given(text=st.text(min_size=0, max_size=300))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_tokenize_is_deterministic(text: str) -> None:
    """Tokenization is pure: same input must always yield the same output."""
    tok = SpanishTokenizer()
    assert tok.tokenize(text) == tok.tokenize(text)


@given(text=st.text(min_size=0, max_size=300))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
def test_tokens_contain_no_stopwords(text: str) -> None:
    """The post-stem stopword filter must remove all SPANISH_STOPWORDS entries."""
    from cenote.tokenizers.spanish import SPANISH_STOPWORDS

    tok = SpanishTokenizer()
    tokens = tok.tokenize(text)
    leaked = [t for t in tokens if t in SPANISH_STOPWORDS]
    assert leaked == [], f"stopwords leaked through: {leaked}"
