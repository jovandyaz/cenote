# SPDX-License-Identifier: Apache-2.0
"""Tests for the cenote.errors exception hierarchy."""

from cenote.errors import (
    CenoteError,
    ConfigurationError,
    DimensionMismatchError,
    EmbeddingError,
    MigrationError,
    RateLimitError,
    VectorStoreError,
)


class TestExceptionHierarchy:
    def test_all_are_cenote_errors(self) -> None:
        for cls in (
            ConfigurationError,
            EmbeddingError,
            RateLimitError,
            VectorStoreError,
            DimensionMismatchError,
            MigrationError,
        ):
            assert issubclass(cls, CenoteError), f"{cls.__name__} is not a CenoteError"

    def test_rate_limit_is_embedding_error(self) -> None:
        assert issubclass(RateLimitError, EmbeddingError)

    def test_dimension_mismatch_is_vector_store_error(self) -> None:
        assert issubclass(DimensionMismatchError, VectorStoreError)

    def test_migration_is_vector_store_error(self) -> None:
        assert issubclass(MigrationError, VectorStoreError)

    def test_errors_carry_messages(self) -> None:
        e = ConfigurationError("bad dim")
        assert str(e) == "bad dim"
