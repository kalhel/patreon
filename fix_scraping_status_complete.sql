-- Fix scraping_status table - Complete fix with data update
-- This script:
-- 1. Renames creator_id → source_id
-- 2. Updates values to match new creator_sources IDs
-- 3. Adds foreign key constraint

BEGIN;

-- Step 1: Rename column (without foreign key yet)
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;
RAISE NOTICE '✅ Step 1: Column renamed creator_id → source_id';

-- Step 2: Update source_id values based on firebase_data->>'creator_id'
-- Map firebase creator_id to new creator_sources.id

-- Create temporary mapping
CREATE TEMP TABLE creator_mapping AS
SELECT
    cs.id as source_id,
    cs.platform_id as firebase_creator_id
FROM creator_sources cs
WHERE cs.platform = 'patreon';

RAISE NOTICE '✅ Step 2: Created mapping table';

-- Show mapping
SELECT 'Mapping:' as info, firebase_creator_id, source_id FROM creator_mapping;

-- Update scraping_status using firebase_data
UPDATE scraping_status ss
SET source_id = cm.source_id
FROM creator_mapping cm
WHERE ss.firebase_data->>'creator_id' = cm.firebase_creator_id;

RAISE NOTICE '✅ Step 3: Updated source_id values based on firebase_data';

-- Verify update
SELECT
    'After Update:' as info,
    source_id,
    COUNT(*) as post_count
FROM scraping_status
GROUP BY source_id
ORDER BY source_id;

-- Step 3: Now add foreign key constraint
ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE;

RAISE NOTICE '✅ Step 4: Foreign key constraint added';

-- Step 4: Update indexes
DROP INDEX IF EXISTS idx_scraping_status_creator;
CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);

RAISE NOTICE '✅ Step 5: Indexes updated';

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
