-- ============================================================================
-- Migration: Add content_text column for paragraph/heading/list search
-- ============================================================================
-- Date: 2025-11-09
-- Purpose: Extract text from content_blocks (paragraphs, headings, lists)
--          to match SQLite FTS5 behavior
--
-- Issue: PostgreSQL was only searching full_content (empty), while SQLite
--        extracts text from content_blocks JSON
--
-- Solution: Add content_text column with extracted paragraph/heading/list text
-- ============================================================================

SET search_path TO public;

\echo '============================================================================'
\echo 'Adding content_text column for content_blocks text search'
\echo '============================================================================'
\echo ''

-- Step 1: Add content_text column
\echo '📝 Step 1: Adding content_text column...'

ALTER TABLE posts ADD COLUMN IF NOT EXISTS content_text TEXT;

COMMENT ON COLUMN posts.content_text IS
'Denormalized text from paragraph/heading/list_item blocks for full-text search.
Extracted from content_blocks JSONB where type IN (''paragraph'', ''heading'', ''list_item'', ''text'').
Updated automatically when content_blocks changes (via trigger).
Used in search_vector with weight B (same priority as full_content).
Added: 2025-11-09 (Fix content search parity with SQLite)';

\echo '✅ Column added'
\echo ''

-- Step 2: Extract text from content_blocks
\echo '📝 Step 2: Extracting text from content_blocks...'

UPDATE posts
SET content_text = (
    SELECT string_agg(block->>'text', ' ')
    FROM jsonb_array_elements(content_blocks) AS block
    WHERE block->>'type' IN ('paragraph', 'heading', 'list_item', 'text')
      AND block->>'text' IS NOT NULL
      AND trim(block->>'text') != ''
)
WHERE content_blocks IS NOT NULL
  AND jsonb_array_length(content_blocks) > 0;

-- Report results
WITH stats AS (
    SELECT
        COUNT(*) FILTER (WHERE content_text IS NOT NULL) as posts_with_content,
        COUNT(*) FILTER (WHERE content_text IS NULL) as posts_without_content,
        COUNT(*) as total_posts
    FROM posts
    WHERE deleted_at IS NULL
)
SELECT
    total_posts,
    posts_with_content,
    posts_without_content,
    ROUND(100.0 * posts_with_content / NULLIF(total_posts, 0), 1) as pct_with_content
FROM stats;

\echo '✅ Content text extracted from content_blocks'
\echo ''

-- Step 3: Update search_vector to use content_text instead of full_content
\echo '📝 Step 3: Updating search_vector to use content_text...'

UPDATE posts
SET search_vector =
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(content_text, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(array_to_string(patreon_tags, ' '), '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(comments_text, '')), 'D') ||
    setweight(to_tsvector('english', COALESCE(subtitles_text, '')), 'D')
WHERE deleted_at IS NULL;

\echo '✅ search_vector updated with content_text'
\echo ''

-- Step 4: Update trigger to extract content_text and use it in search_vector
\echo '📝 Step 4: Updating trigger...'

DROP TRIGGER IF EXISTS posts_search_vector_trigger ON posts;

CREATE OR REPLACE FUNCTION posts_search_vector_update()
RETURNS trigger AS $$
BEGIN
    -- Extract text from content_blocks if changed
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.content_blocks IS DISTINCT FROM OLD.content_blocks) THEN
        -- Extract paragraph/heading/list_item/text blocks
        NEW.content_text := (
            SELECT string_agg(block->>'text', ' ')
            FROM jsonb_array_elements(NEW.content_blocks) AS block
            WHERE block->>'type' IN ('paragraph', 'heading', 'list_item', 'text')
              AND block->>'text' IS NOT NULL
              AND trim(block->>'text') != ''
        );

        -- Extract comments
        NEW.comments_text := (
            SELECT string_agg(block->>'text', ' ')
            FROM jsonb_array_elements(NEW.content_blocks) AS block
            WHERE block->>'type' = 'comment'
              AND block->>'text' IS NOT NULL
              AND trim(block->>'text') != ''
        );
    END IF;

    -- Update search_vector with content_text (not full_content)
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content_text, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.patreon_tags, ' '), '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.comments_text, '')), 'D') ||
        setweight(to_tsvector('english', COALESCE(NEW.subtitles_text, '')), 'D');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, patreon_tags, content_blocks, subtitles_text
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_update();

\echo '✅ Trigger updated to use content_text'
\echo ''

-- Step 5: Verification
\echo '============================================================================'
\echo '✅ Migration Complete - Verification'
\echo '============================================================================'
\echo ''

\echo 'Sample posts with content_text:';
SELECT
    post_id,
    substring(title, 1, 50) as title,
    length(content_text) as content_chars,
    substring(content_text, 1, 80) || '...' as content_sample
FROM posts
WHERE content_text IS NOT NULL
  AND deleted_at IS NULL
ORDER BY length(content_text) DESC
LIMIT 3;

\echo ''
\echo 'Content search coverage:';
SELECT
    COUNT(*) FILTER (WHERE content_text IS NOT NULL) as with_content,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE content_text IS NOT NULL) / COUNT(*), 1) as pct
FROM posts
WHERE deleted_at IS NULL;

\echo ''
\echo '============================================================================'
\echo 'Content text now searchable!'
\echo 'Test: SELECT post_id, title FROM posts WHERE search_vector @@ to_tsquery(''english'', ''astrology'') LIMIT 5;'
\echo '============================================================================'
