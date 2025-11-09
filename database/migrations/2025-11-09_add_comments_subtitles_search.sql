-- ============================================================================
-- Migration: Add Comments and Subtitles to Full-Text Search
-- ============================================================================
-- Date: 2025-11-09
-- Author: Javi + Claude
-- Branch: feature/advanced-search-improvements
-- Context: Fase 2 - Expand search coverage
--
-- Purpose:
--   Add dedicated columns for comments and subtitles text to enable
--   full-text search in these fields and improve search relevance.
--
-- Approach: HYBRID (Recommended in DATABASE_DESIGN_REVIEW.md)
--   - Add comments_text column (extracted from content_blocks JSONB)
--   - Add subtitles_text column (populated from .vtt files via Python)
--   - Include both in search_vector with weight 'D' (lowest priority)
--   - Keep content_blocks intact for rendering
--
-- Rollback: See 2025-11-09_rollback_comments_subtitles_search.sql
-- ============================================================================

-- Set search path
SET search_path TO public;

\echo '============================================================================'
\echo 'Fase 2: Adding Comments and Subtitles Search Support'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- STEP 1: Add new columns for searchable text
-- ============================================================================

\echo '📝 Step 1: Adding columns comments_text and subtitles_text...'

-- Add comments_text column
ALTER TABLE posts ADD COLUMN IF NOT EXISTS comments_text TEXT;

-- Add subtitles_text column
ALTER TABLE posts ADD COLUMN IF NOT EXISTS subtitles_text TEXT;

-- Add documentation
COMMENT ON COLUMN posts.comments_text IS
'Denormalized text from all comments for full-text search.
Extracted from content_blocks JSONB where type = ''comment''.
Updated automatically when content_blocks changes (via trigger).
Used in search_vector with weight D (lowest priority).
Added: 2025-11-09 (Fase 2)';

COMMENT ON COLUMN posts.subtitles_text IS
'Denormalized text from video subtitles (.vtt files) for full-text search.
Populated by Python script from data/media/videos/*.vtt files.
Used in search_vector with weight D (lowest priority).
Added: 2025-11-09 (Fase 2)';

\echo '✅ Columns added successfully'
\echo ''

-- ============================================================================
-- STEP 2: Populate comments_text from content_blocks
-- ============================================================================

\echo '📝 Step 2: Extracting comments from content_blocks JSONB...'

UPDATE posts
SET comments_text = (
    SELECT string_agg(block->>'text', ' ')
    FROM jsonb_array_elements(content_blocks) AS block
    WHERE block->>'type' = 'comment'
      AND block->>'text' IS NOT NULL
      AND trim(block->>'text') != ''
)
WHERE content_blocks IS NOT NULL
  AND jsonb_array_length(content_blocks) > 0;

-- Report results
WITH stats AS (
    SELECT
        COUNT(*) FILTER (WHERE comments_text IS NOT NULL) as posts_with_comments,
        COUNT(*) FILTER (WHERE comments_text IS NULL) as posts_without_comments,
        COUNT(*) as total_posts
    FROM posts
    WHERE deleted_at IS NULL
)
SELECT
    total_posts,
    posts_with_comments,
    posts_without_comments,
    ROUND(100.0 * posts_with_comments / NULLIF(total_posts, 0), 1) as pct_with_comments
FROM stats;

\echo '✅ Comments extracted from content_blocks'
\echo ''

-- ============================================================================
-- STEP 3: Prepare for subtitles (populated by Python script)
-- ============================================================================

\echo '📝 Step 3: Subtitles column ready (will be populated by Python script)'
\echo '   Script: database/migrations/populate_subtitles_text.py'
\echo '   Source: data/media/videos/*.vtt files'
\echo ''

-- Note: subtitles_text will be populated by Python script
-- See: database/migrations/populate_subtitles_text.py

-- ============================================================================
-- STEP 4: Update search_vector to include comments and subtitles
-- ============================================================================

\echo '📝 Step 4: Updating search_vector to include comments and subtitles...'

-- Update all posts to rebuild search_vector with new fields
UPDATE posts
SET search_vector =
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(full_content, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(array_to_string(patreon_tags, ' '), '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(comments_text, '')), 'D') ||
    setweight(to_tsvector('english', COALESCE(subtitles_text, '')), 'D')
WHERE deleted_at IS NULL;

\echo '✅ search_vector updated with comments and subtitles'
\echo ''

-- ============================================================================
-- STEP 5: Update trigger function to maintain search_vector
-- ============================================================================

\echo '📝 Step 5: Updating trigger to include comments and subtitles...'

-- Drop existing trigger
DROP TRIGGER IF EXISTS posts_search_vector_trigger ON posts;

-- Update trigger function
CREATE OR REPLACE FUNCTION posts_search_vector_update()
RETURNS trigger AS $$
BEGIN
    -- Extract comments from content_blocks if changed
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.content_blocks IS DISTINCT FROM OLD.content_blocks) THEN
        NEW.comments_text := (
            SELECT string_agg(block->>'text', ' ')
            FROM jsonb_array_elements(NEW.content_blocks) AS block
            WHERE block->>'type' = 'comment'
              AND block->>'text' IS NOT NULL
              AND trim(block->>'text') != ''
        );
    END IF;

    -- Update search_vector with all searchable fields
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.full_content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.patreon_tags, ' '), '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.comments_text, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.subtitles_text, '')), 'D');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate trigger
CREATE TRIGGER posts_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, full_content, patreon_tags, content_blocks, subtitles_text
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_update();

\echo '✅ Trigger updated to automatically maintain comments_text and search_vector'
\echo ''

-- ============================================================================
-- STEP 6: Verification
-- ============================================================================

\echo '============================================================================'
\echo '✅ Migration Complete - Verification'
\echo '============================================================================'
\echo ''

\echo 'Sample posts with comments:'
SELECT
    post_id,
    substring(title, 1, 50) as title,
    length(comments_text) as comment_chars,
    substring(comments_text, 1, 80) || '...' as comment_sample
FROM posts
WHERE comments_text IS NOT NULL
  AND deleted_at IS NULL
ORDER BY length(comments_text) DESC
LIMIT 3;

\echo ''
\echo 'Search coverage summary:'
SELECT
    COUNT(*) FILTER (WHERE search_vector @@ to_tsquery('english', 'comment')) as searchable_posts,
    COUNT(*) as total_posts,
    ROUND(100.0 * COUNT(*) FILTER (WHERE search_vector @@ to_tsquery('english', 'comment')) / NULLIF(COUNT(*), 0), 1) as pct_searchable
FROM posts
WHERE deleted_at IS NULL;

\echo ''
\echo '============================================================================'
\echo '📋 Next Steps'
\echo '============================================================================'
\echo '1. Run Python script to populate subtitles_text:'
\echo '   python3 database/migrations/populate_subtitles_text.py'
\echo ''
\echo '2. Update web/viewer.py to detect comment/subtitle matches'
\echo ''
\echo '3. Test search for terms that appear in comments'
\echo ''
\echo 'Rollback: database/migrations/2025-11-09_rollback_comments_subtitles_search.sql'
\echo '============================================================================'
