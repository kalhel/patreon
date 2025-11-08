-- =====================================================
-- PATREON POSTS - POSTGRESQL SCHEMA
-- Complete schema for posts, collections, and search
-- =====================================================

-- Drop existing tables if needed (be careful in production!)
-- DROP TABLE IF EXISTS post_collections CASCADE;
-- DROP TABLE IF EXISTS collections CASCADE;
-- DROP TABLE IF EXISTS posts CASCADE;

-- =====================================================
-- MAIN POSTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS posts (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(50) UNIQUE NOT NULL,
    creator_id VARCHAR(100) NOT NULL,
    post_url TEXT NOT NULL,

    -- Content
    title TEXT,
    full_content TEXT,  -- Full text for searching
    content_blocks JSONB,  -- Structured content blocks

    -- Metadata
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    scraped_at TIMESTAMP,

    -- Post metadata from Patreon
    creator_name VARCHAR(200),
    creator_avatar TEXT,

    -- Engagement metrics
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,

    -- Media URLs (remote)
    images TEXT[],  -- Array of image URLs
    videos TEXT[],  -- Array of video URLs
    audios TEXT[],  -- Array of audio URLs
    attachments TEXT[],  -- Array of attachment URLs

    -- Local media paths (downloaded files)
    image_local_paths TEXT[],
    video_local_paths TEXT[],
    audio_local_paths TEXT[],

    -- Video-specific data
    video_downloads TEXT[],
    video_streams JSONB,  -- HLS stream info
    video_subtitles JSONB,  -- Subtitle files info

    -- Tags and categorization
    patreon_tags TEXT[],  -- Tags from Patreon

    -- Processing status
    status JSONB DEFAULT '{
        "url_collected": false,
        "details_extracted": false,
        "media_downloaded": false,
        "uploaded_to_notion": false,
        "attempt_count": 0,
        "last_attempt": null
    }'::JSONB,

    -- Full-text search vector (for fast text search)
    search_vector tsvector,

    -- Soft delete
    deleted_at TIMESTAMP DEFAULT NULL,

    -- Indexes will be created below
    CONSTRAINT post_id_not_empty CHECK (post_id <> ''),
    CONSTRAINT creator_id_not_empty CHECK (creator_id <> '')
);

-- =====================================================
-- COLLECTIONS TABLE (for Phase 3)
-- =====================================================
CREATE TABLE IF NOT EXISTS collections (
    -- Primary identifiers
    id SERIAL PRIMARY KEY,
    collection_id VARCHAR(50) UNIQUE NOT NULL,
    creator_id VARCHAR(100) NOT NULL,

    -- Collection info
    title VARCHAR(500) NOT NULL,
    description TEXT,
    collection_url TEXT,

    -- Metadata
    post_count INTEGER DEFAULT 0,  -- Number of posts in collection

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    scraped_at TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP DEFAULT NULL,

    CONSTRAINT collection_id_not_empty CHECK (collection_id <> '')
);

-- =====================================================
-- POST-COLLECTION RELATIONSHIP (Many-to-Many)
-- =====================================================
CREATE TABLE IF NOT EXISTS post_collections (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(50) NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    collection_id VARCHAR(50) NOT NULL REFERENCES collections(collection_id) ON DELETE CASCADE,

    -- Order of post within collection
    order_in_collection INTEGER,

    -- Timestamps
    added_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint: each post can only be in a collection once
    CONSTRAINT unique_post_collection UNIQUE (post_id, collection_id)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Primary lookups
CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);
CREATE INDEX IF NOT EXISTS idx_posts_creator_id ON posts(creator_id);
CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);

-- Search indexes
CREATE INDEX IF NOT EXISTS idx_posts_search_vector ON posts USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_posts_title ON posts USING GIN(to_tsvector('english', COALESCE(title, '')));

-- Tag searches
CREATE INDEX IF NOT EXISTS idx_posts_tags ON posts USING GIN(patreon_tags);

-- Status tracking
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts USING GIN(status);

-- Collections
CREATE INDEX IF NOT EXISTS idx_collections_creator_id ON collections(creator_id);
CREATE INDEX IF NOT EXISTS idx_post_collections_post_id ON post_collections(post_id);
CREATE INDEX IF NOT EXISTS idx_post_collections_collection_id ON post_collections(collection_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_posts_creator_published ON posts(creator_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_creator_likes ON posts(creator_id, like_count DESC);

-- Soft delete support
CREATE INDEX IF NOT EXISTS idx_posts_not_deleted ON posts(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- FUNCTIONS FOR AUTOMATIC UPDATES
-- =====================================================

-- Function to update search_vector automatically
CREATE OR REPLACE FUNCTION posts_search_vector_update() RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.full_content, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.patreon_tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update search_vector
DROP TRIGGER IF EXISTS posts_search_vector_trigger ON posts;
CREATE TRIGGER posts_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, full_content, patreon_tags
    ON posts
    FOR EACH ROW
    EXECUTE FUNCTION posts_search_vector_update();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for posts.updated_at
DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for collections.updated_at
DROP TRIGGER IF EXISTS update_collections_updated_at ON collections;
CREATE TRIGGER update_collections_updated_at
    BEFORE UPDATE ON collections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- HELPER VIEWS
-- =====================================================

-- View: Posts with collection info
CREATE OR REPLACE VIEW posts_with_collections AS
SELECT
    p.*,
    COALESCE(json_agg(
        json_build_object(
            'collection_id', c.collection_id,
            'title', c.title,
            'order', pc.order_in_collection
        )
    ) FILTER (WHERE c.collection_id IS NOT NULL), '[]'::json) as collections
FROM posts p
LEFT JOIN post_collections pc ON p.post_id = pc.post_id
LEFT JOIN collections c ON pc.collection_id = c.collection_id
WHERE p.deleted_at IS NULL
GROUP BY p.id;

-- View: Collection statistics
CREATE OR REPLACE VIEW collection_stats AS
SELECT
    c.collection_id,
    c.title,
    c.creator_id,
    COUNT(pc.post_id) as actual_post_count,
    c.post_count as declared_post_count,
    c.created_at,
    c.updated_at
FROM collections c
LEFT JOIN post_collections pc ON c.collection_id = pc.collection_id
WHERE c.deleted_at IS NULL
GROUP BY c.collection_id, c.title, c.creator_id, c.post_count, c.created_at, c.updated_at;

-- View: Creator statistics
CREATE OR REPLACE VIEW creator_stats AS
SELECT
    creator_id,
    creator_name,
    COUNT(*) as total_posts,
    SUM(like_count) as total_likes,
    SUM(comment_count) as total_comments,
    AVG(like_count) as avg_likes_per_post,
    COUNT(*) FILTER (WHERE array_length(images, 1) > 0) as posts_with_images,
    COUNT(*) FILTER (WHERE array_length(videos, 1) > 0) as posts_with_videos,
    COUNT(*) FILTER (WHERE array_length(audios, 1) > 0) as posts_with_audio,
    MIN(published_at) as first_post_date,
    MAX(published_at) as latest_post_date
FROM posts
WHERE deleted_at IS NULL
GROUP BY creator_id, creator_name;

-- =====================================================
-- USEFUL QUERY FUNCTIONS
-- =====================================================

-- Function: Search posts by text
CREATE OR REPLACE FUNCTION search_posts(search_query TEXT)
RETURNS TABLE (
    post_id VARCHAR(50),
    title TEXT,
    creator_id VARCHAR(100),
    published_at TIMESTAMP,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.post_id,
        p.title,
        p.creator_id,
        p.published_at,
        ts_rank(p.search_vector, plainto_tsquery('english', search_query)) as rank
    FROM posts p
    WHERE p.search_vector @@ plainto_tsquery('english', search_query)
        AND p.deleted_at IS NULL
    ORDER BY rank DESC, p.published_at DESC
    LIMIT 100;
END;
$$ LANGUAGE plpgsql;

-- Function: Get posts by tag
CREATE OR REPLACE FUNCTION get_posts_by_tag(tag_name TEXT)
RETURNS TABLE (
    post_id VARCHAR(50),
    title TEXT,
    creator_id VARCHAR(100),
    published_at TIMESTAMP,
    like_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.post_id,
        p.title,
        p.creator_id,
        p.published_at,
        p.like_count
    FROM posts p
    WHERE tag_name = ANY(p.patreon_tags)
        AND p.deleted_at IS NULL
    ORDER BY p.published_at DESC
    LIMIT 100;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON TABLE posts IS 'Main table storing all Patreon posts with full content and metadata';
COMMENT ON TABLE collections IS 'Patreon collections grouping related posts';
COMMENT ON TABLE post_collections IS 'Many-to-many relationship between posts and collections';
COMMENT ON COLUMN posts.search_vector IS 'Full-text search vector (auto-generated from title, content, tags)';
COMMENT ON COLUMN posts.content_blocks IS 'Structured content as JSONB (paragraphs, images, videos, etc.)';
COMMENT ON COLUMN posts.status IS 'Processing status tracking (scraping, downloads, uploads)';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Schema created successfully!';
    RAISE NOTICE '📊 Tables: posts, collections, post_collections';
    RAISE NOTICE '🔍 Indexes: Full-text search, tags, creator, timestamps';
    RAISE NOTICE '👁️  Views: posts_with_collections, collection_stats, creator_stats';
    RAISE NOTICE '🔧 Functions: search_posts(), get_posts_by_tag()';
END $$;
