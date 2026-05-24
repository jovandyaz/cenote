-- Migration 002: change primary key from (id) to (namespace, id).
--
-- The protocol contract is that a chunk id is unique within a namespace,
-- not globally. The InMemoryVectorStore enforces this via dict[ns][id].
-- 001_init.sql shipped with `id TEXT PRIMARY KEY` which collides across
-- namespaces when downstream products reuse chunk ids per tenant. This
-- migration aligns PgVectorStore with the protocol.

ALTER TABLE cenote_chunks DROP CONSTRAINT IF EXISTS cenote_chunks_pkey;
ALTER TABLE cenote_chunks ADD PRIMARY KEY (namespace, id);
