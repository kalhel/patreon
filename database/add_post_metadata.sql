-- =====================================================
-- Add post_metadata column to posts table
-- =====================================================

-- Add post_metadata column (stores extracted metadata from HTML)
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS post_metadata JSONB;

-- Create index for faster metadata queries
CREATE INDEX IF NOT EXISTS idx_posts_metadata ON posts USING GIN(post_metadata);

-- Verify column was added
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'posts'
AND column_name = 'post_metadata';

-- Show current state
SELECT
    COUNT(*) as total_posts,
    COUNT(post_metadata) as with_metadata
FROM posts
WHERE deleted_at IS NULL;
