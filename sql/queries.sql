-- sql/queries.sql
-- Reference queries for the `calls` table in calls.db
-- Run with:  sqlite3 calls.db < sql/queries.sql
--        or: sqlite3 calls.db ".read sql/queries.sql"

-- ── 1. SELECT * — every column, every row ─────────────────────────────────────
SELECT * FROM calls;

-- ── 2. Column-subset SELECT — the fields most relevant for a dashboard ─────────
SELECT
    id,
    caller_name,
    intent,
    callback_number,
    audio_filename,
    created_at
FROM calls
ORDER BY id DESC;

-- ── 3. COUNT(*) — total number of processed calls ─────────────────────────────
SELECT COUNT(*) AS total_calls FROM calls;
