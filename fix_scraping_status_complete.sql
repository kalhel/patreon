-- Fix scraping_status table - Complete fix with data update
-- This script:
-- 1. Renames creator_id → source_id
-- 2. Updates values to match new creator_sources IDs
-- 3. Adds foreign key constraint

BEGIN;

\echo ''
\echo '✅ Step 1: Renaming column creator_id → source_id...'
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;

\echo ''
\echo '✅ Step 2: Creating mapping table...'
-- Create temporary mapping
CREATE TEMP TABLE creator_mapping AS
SELECT
    cs.id as source_id,
    cs.platform_id as firebase_creator_id
FROM creator_sources cs
WHERE cs.platform = 'patreon';

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  Mapping: firebase_creator_id → source_id'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT firebase_creator_id, source_id FROM creator_mapping ORDER BY firebase_creator_id;

\echo ''
\echo '✅ Step 3: Updating source_id values based on firebase_data...'
UPDATE scraping_status ss
SET source_id = cm.source_id
FROM creator_mapping cm
WHERE ss.firebase_data->>'creator_id' = cm.firebase_creator_id;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  Distribution after update'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
SELECT
    source_id,
    COUNT(*) as post_count
FROM scraping_status
GROUP BY source_id
ORDER BY source_id;

\echo ''
\echo '✅ Step 4: Adding foreign key constraint...'
ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE;

\echo ''
\echo '✅ Step 5: Updating indexes...'
DROP INDEX IF EXISTS idx_scraping_status_creator;
CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);

COMMIT;

-- Final verification
\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  Final Verification'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT
    c.name as creator_name,
    cs.platform,
    cs.platform_id,
    COUNT(ss.id) as post_count
FROM creators c
JOIN creator_sources cs ON cs.creator_id = c.id
LEFT JOIN scraping_status ss ON ss.source_id = cs.id
GROUP BY c.name, cs.platform, cs.platform_id
ORDER BY c.name;
