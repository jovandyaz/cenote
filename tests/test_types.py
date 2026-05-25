# SPDX-License-Identifier: Apache-2.0
"""Smoke tests for cenote.types — verify aliases are importable and usable."""

from cenote.types import ContentHash, ModelId, Namespace, Vector


def test_vector_alias_accepts_list_of_floats() -> None:
    v: Vector = [1.0, 2.5, -3.14]
    assert abs(sum(v) - 0.36) < 1e-9
    assert len(v) == 3


def test_namespace_alias_is_str() -> None:
    ns: Namespace = "tenant-a"
    assert isinstance(ns, str)


def test_model_id_alias_is_str() -> None:
    m: ModelId = "voyage:voyage-3"
    assert isinstance(m, str)


def test_content_hash_alias_is_str() -> None:
    h: ContentHash = "a" * 64
    assert isinstance(h, str)
    assert len(h) == 64
