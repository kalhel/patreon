-- Performance Optimization Indexes for Web Viewer
-- Date: 2025-11-08
-- Purpose: Improve query performance for web viewer load times

-- Index for deleted_at filter (most common WHERE clause in web viewer)
-- This speeds up: WHERE deleted_at IS NULL
CREATE INDEX IF NOT EXISTS idx_posts_not_deleted
ON posts(deleted_at)
WHERE deleted_at IS NULL;

-- Index for collections deleted_at filter
CREATE INDEX IF NOT EXISTS idx_collections_not_deleted
ON collections(deleted_at)
WHERE deleted_at IS NULL;

-- Composite index for post_collections JOIN (used in load_posts_from_postgres)
CREATE INDEX IF NOT EXISTS idx_post_collections_post
ON post_collections(post_id);

CREATE INDEX IF NOT EXISTS idx_post_collections_collection
ON post_collections(collection_id);

-- Composite index for frequent collection queries
CREATE INDEX IF NOT EXISTS idx_post_collections_composite
ON post_collections(collection_id, post_id, order_in_collection);

-- Index on creator_id for filtering posts by creator
-- (Already exists as idx_posts_creator, but verifying)
-- CREATE INDEX IF NOT EXISTS idx_posts_creator ON posts(creator_id);

-- Index on published_at for ordering posts by date
-- (Already exists as idx_posts_published, but verifying)
-- CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published_at DESC);

-- Add statistics for query planner
ANALYZE posts;
ANALYZE collections;
ANALYZE post_collections;

-- Verify indexes were created
\di idx_posts_not_deleted
\di idx_collections_not_deleted
\di idx_post_collections_post
\di idx_post_collections_collection
\di idx_post_collections_composite
