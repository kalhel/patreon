-- Fix scraping_status table to use Schema V2 (source_id instead of creator_id)
-- This updates the table structure to match the multi-source design

BEGIN;

-- Step 1: Drop old foreign key constraint (if exists)
ALTER TABLE scraping_status DROP CONSTRAINT IF EXISTS scraping_status_creator_id_fkey;

-- Step 2: Rename column creator_id → source_id
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;

-- Step 3: Add new foreign key to creator_sources
ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE;

-- Step 4: Drop old index and create new one
DROP INDEX IF EXISTS idx_scraping_status_creator;
CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);

-- Step 5: Update unique constraint (if needed)
-- Note: scraping_status_post_id_key already exists (post_id is unique)
-- We could add: UNIQUE(source_id, post_id) for multi-source, but post_id is already globally unique

-- Step 6: Verify the change
DO $$
DECLARE
    col_exists boolean;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'scraping_status' AND column_name = 'source_id'
    ) INTO col_exists;

    IF col_exists THEN
        RAISE NOTICE '✅ Column renamed: creator_id → source_id';
    ELSE
        RAISE EXCEPTION '❌ Failed to rename column';
    END IF;
END $$;

COMMIT;

-- Verification query
SELECT
    'scraping_status' as table_name,
    COUNT(*) as total_rows,
    COUNT(source_id) as rows_with_source_id,
    COUNT(DISTINCT source_id) as unique_sources
FROM scraping_status;
