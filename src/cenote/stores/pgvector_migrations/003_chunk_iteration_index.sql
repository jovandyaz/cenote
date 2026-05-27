-- Supports paginated chunk iteration by stable (namespace, id) order.
-- The primary key already covers (namespace, id), so this is a no-op in
-- practice — but we add it as an explicit migration so future restructures
-- (e.g. partitioning) keep iteration deterministic.

-- Intentionally empty: PRIMARY KEY (namespace, id) from migration 002
-- already provides the index needed for `ORDER BY namespace, id`.
SELECT 1;
