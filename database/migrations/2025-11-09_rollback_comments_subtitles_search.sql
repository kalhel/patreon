-- ============================================================================
-- ROLLBACK: Remove Comments and Subtitles Search Support
-- ============================================================================
-- Date: 2025-11-09
-- Purpose: Rollback migration 2025-11-09_add_comments_subtitles_search.sql
--
-- This script:
--   1. Removes comments_text and subtitles_text columns
--   2. Restores original search_vector (without comments/subtitles)
--   3. Restores original trigger function
--
-- WARNING: This will permanently delete comments_text and subtitles_text data!
-- ============================================================================

-- Set search path
SET search_path TO public;

\echo '============================================================================'
\echo 'ROLLBACK: Removing Comments and Subtitles Search Support'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- STEP 1: Restore original trigger function (without comments/subtitles)
-- ============================================================================

\echo '📝 Step 1: Restoring original trigger function...'

DROP TRIGGER IF EXISTS posts_search_vector_trigger ON posts;

CREATE OR REPLACE FUNCTION posts_search_vector_update()
RETURNS trigger AS $$
BEGIN
    -- Original search_vector (without comments and subtitles)
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.full_content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.patreon_tags, ' '), '')), 'C');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, full_content, patreon_tags
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_update();

\echo '✅ Trigger restored to original version'
\echo ''

-- ============================================================================
-- STEP 2: Rebuild search_vector without comments/subtitles
-- ============================================================================

\echo '📝 Step 2: Rebuilding search_vector without comments and subtitles...'

UPDATE posts
SET search_vector =
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(full_content, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(array_to_string(patreon_tags, ' '), '')), 'C')
WHERE deleted_at IS NULL;

\echo '✅ search_vector rebuilt without comments and subtitles'
\echo ''

-- ============================================================================
-- STEP 3: Remove columns
-- ============================================================================

\echo '📝 Step 3: Removing comments_text and subtitles_text columns...'
\echo '⚠️  WARNING: This will permanently delete data in these columns!'
\echo ''

ALTER TABLE posts DROP COLUMN IF EXISTS comments_text;
ALTER TABLE posts DROP COLUMN IF EXISTS subtitles_text;

\echo '✅ Columns removed'
\echo ''

-- ============================================================================
-- STEP 4: Verification
-- ============================================================================

\echo '============================================================================'
\echo '✅ Rollback Complete'
\echo '============================================================================'
\echo ''

\echo 'Verify columns removed:'
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'posts'
  AND column_name IN ('comments_text', 'subtitles_text');

\echo ''
\echo '(Should return 0 rows if rollback successful)'
\echo ''

\echo '============================================================================'
\echo 'To re-apply the migration:'
\echo 'PGPASSWORD=''your_password'' psql -U patreon_user -d alejandria -h 127.0.0.1 \\'
\echo '  -f database/migrations/2025-11-09_add_comments_subtitles_search.sql'
\echo '============================================================================'
