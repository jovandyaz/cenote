-- Migration 001: initial schema for cenote_chunks.
-- Note: this file MUST NOT be edited once committed. Add a new file
-- (002_<name>.sql, ...) for schema changes.
--
-- Performance notes:
--   - HNSW params (m, ef_construction) are tunable via the {HNSW_M},
--     {HNSW_EF_CONSTRUCTION} template variables, bound by PgVectorStore.
--   - For corpora >100k vectors, set `SET maintenance_work_mem = '2GB'`
--     in the session before applying this migration (HNSW build is
--     memory-bound and slows ~10x without it).
--   - GIN index on metadata enables fast JSONB `@>` containment filters.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS cenote_chunks (
    id              TEXT PRIMARY KEY,
    namespace       TEXT NOT NULL,
    document_id     TEXT NOT NULL,
    content         TEXT NOT NULL,
    position        INT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_hash    TEXT NOT NULL,
    embedding       vector({DIMENSIONS}) NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cenote_chunks_namespace_doc_idx
    ON cenote_chunks (namespace, document_id);

CREATE INDEX IF NOT EXISTS cenote_chunks_metadata_gin_idx
    ON cenote_chunks USING gin (metadata);

CREATE INDEX IF NOT EXISTS cenote_chunks_embedding_hnsw_idx
    ON cenote_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION});
