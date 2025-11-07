-- Fix scraping_status table: rename creator_id to source_id
-- This completes the Schema V2 migration

BEGIN;

-- Drop old foreign key constraint
ALTER TABLE scraping_status DROP CONSTRAINT IF EXISTS scraping_status_creator_id_fkey;

-- Rename column
ALTER TABLE scraping_status RENAME COLUMN creator_id TO source_id;

-- Drop old index
DROP INDEX IF EXISTS idx_scraping_status_creator;

-- Add new foreign key to creator_sources
ALTER TABLE scraping_status
    ADD CONSTRAINT scraping_status_source_id_fkey
    FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE;

-- Create new index
CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);

-- Update unique constraint to match V2
ALTER TABLE scraping_status DROP CONSTRAINT IF EXISTS scraping_status_post_id_key;
ALTER TABLE scraping_status ADD CONSTRAINT scraping_status_source_post_unique UNIQUE(source_id, post_id);

COMMIT;

-- Verify
\d scraping_status
