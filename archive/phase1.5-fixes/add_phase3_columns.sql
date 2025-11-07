-- Add missing phase3 columns to scraping_status
-- Complete Schema V2 migration

BEGIN;

-- Add phase3 columns
ALTER TABLE scraping_status
    ADD COLUMN IF NOT EXISTS phase3_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS phase3_completed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS phase3_attempts INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS phase3_last_error TEXT;

-- Create phase3 index
CREATE INDEX IF NOT EXISTS idx_scraping_status_phase3
    ON scraping_status(phase3_status)
    WHERE phase3_status = 'pending';

-- Verify columns added
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'scraping_status'
      AND column_name IN ('phase3_status', 'phase3_completed_at', 'phase3_attempts', 'phase3_last_error');

    IF col_count = 4 THEN
        RAISE NOTICE '✅ All phase3 columns added successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to add all phase3 columns (only % of 4)', col_count;
    END IF;
END $$;

COMMIT;

\echo ''
\echo '✅ Phase3 columns added to scraping_status'
\echo 'Schema V2 is now complete'
