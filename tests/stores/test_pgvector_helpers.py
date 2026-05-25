# SPDX-License-Identifier: Apache-2.0
"""Unit tests for PgVectorStore pure helpers (no Postgres required)."""

import pytest

from cenote.errors import ConfigurationError
from cenote.stores.pgvector import PgVectorStore, _vector_literal


class TestVectorLiteral:
    def test_empty_list(self) -> None:
        assert _vector_literal([]) == "[]"

    def test_three_floats(self) -> None:
        result = _vector_literal([1.0, 2.5, -3.14])
        assert result.startswith("[") and result.endswith("]")
        parts = result[1:-1].split(",")
        assert len(parts) == 3
        assert float(parts[0]) == 1.0
        assert float(parts[1]) == 2.5
        assert float(parts[2]) == pytest.approx(-3.14)

    def test_roundtrip_preserves_floats(self) -> None:
        original = [0.123456789012345, 1e-10, -1e10]
        result = _vector_literal(original)
        parsed = [float(x) for x in result[1:-1].split(",")]
        assert parsed == original, f"roundtrip lost precision: {parsed} != {original}"


class TestMigrationDiscovery:
    def test_migration_files_returns_sorted_sql_only(self) -> None:
        files = PgVectorStore._migration_files()
        assert all(f.endswith(".sql") for f in files), f"non-SQL in migrations: {files}"
        assert files == sorted(files), "migrations not sorted"
        assert "001_init.sql" in files
        assert "002_namespace_id_pk.sql" in files

    def test_read_migration_includes_template_placeholders(self) -> None:
        content = PgVectorStore._read_migration("001_init.sql")
        assert "{DIMENSIONS}" in content
        assert "{HNSW_M}" in content
        assert "{HNSW_EF_CONSTRUCTION}" in content


class TestConstructorValidation:
    @pytest.fixture
    def fake_pool(self) -> object:
        return object()

    def test_rejects_zero_dimensions(self, fake_pool: object) -> None:
        with pytest.raises(ConfigurationError, match="dimensions must be positive"):
            PgVectorStore(pool=fake_pool, dimensions=0)  # type: ignore[arg-type]

    def test_rejects_negative_dimensions(self, fake_pool: object) -> None:
        with pytest.raises(ConfigurationError):
            PgVectorStore(pool=fake_pool, dimensions=-1)  # type: ignore[arg-type]

    def test_rejects_zero_hnsw_m(self, fake_pool: object) -> None:
        with pytest.raises(ConfigurationError, match=r"hnsw_m.*must be positive"):
            PgVectorStore(pool=fake_pool, dimensions=128, hnsw_m=0)  # type: ignore[arg-type]

    def test_rejects_zero_hnsw_ef_construction(self, fake_pool: object) -> None:
        with pytest.raises(ConfigurationError):
            PgVectorStore(pool=fake_pool, dimensions=128, hnsw_ef_construction=0)  # type: ignore[arg-type]

    def test_accepts_valid_defaults(self, fake_pool: object) -> None:
        store = PgVectorStore(pool=fake_pool, dimensions=128)  # type: ignore[arg-type]
        assert store._dimensions == 128
        assert store._table == "cenote_chunks"
        assert store._hnsw_m == 16
        assert store._hnsw_ef_construction == 64
        assert store._hnsw_ef_search is None

    def test_accepts_custom_params(self, fake_pool: object) -> None:
        store = PgVectorStore(  # type: ignore[arg-type]
            pool=fake_pool,
            dimensions=1536,
            table_name="my_chunks",
            hnsw_m=32,
            hnsw_ef_construction=128,
            hnsw_ef_search=200,
        )
        assert store._dimensions == 1536
        assert store._table == "my_chunks"
        assert store._hnsw_m == 32
        assert store._hnsw_ef_construction == 128
        assert store._hnsw_ef_search == 200
