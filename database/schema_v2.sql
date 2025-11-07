-- ============================================================================
-- Patreon Multi-Source Content Aggregator - PostgreSQL Database Schema V2
-- ============================================================================
-- Version: 2.0
-- Date: 2025-11-07
-- Description: Multi-source schema supporting multiple platforms per creator
-- Changes from V1:
--   - Separated creators (entities) from sources (platforms)
--   - One creator can have multiple sources (Patreon, YouTube, Substack, etc)
--   - Posts now reference creator_sources instead of creators directly
--   - Avatar storage: filesystem (web/static/avatars/) + DB reference
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- CORE ENTITIES (Multi-Source Design)
-- ============================================================================

-- ============================================
-- CREATORS: Personas/Entidades (Platform-agnostic)
-- ============================================
CREATE TABLE creators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- Unique creator name (e.g., "Astrobymax")
    display_name VARCHAR(255),          -- Optional display name override
    description TEXT,                   -- Bio/description

    -- Avatar (stored in filesystem: web/static/avatars/)
    avatar_filename VARCHAR(255),       -- e.g., "astrobymax.jpg" (NULL = use default)

    -- Links
    website_url VARCHAR(500),           -- Personal website

    -- Status
    active BOOLEAN DEFAULT true,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE creators IS 'Content creators (platform-agnostic entities)';
COMMENT ON COLUMN creators.name IS 'Unique creator name used across all platforms';
COMMENT ON COLUMN creators.avatar_filename IS 'Filename of avatar stored in web/static/avatars/ (NULL uses default.jpg)';
COMMENT ON COLUMN creators.metadata IS 'Additional creator metadata (social links, etc)';

-- ============================================
-- CREATOR SOURCES: Platform-specific channels
-- ============================================
CREATE TABLE creator_sources (
    id SERIAL PRIMARY KEY,
    creator_id INTEGER NOT NULL REFERENCES creators(id) ON DELETE CASCADE,

    -- Platform identification
    platform VARCHAR(100) NOT NULL,         -- 'patreon', 'youtube', 'substack', 'spotify', etc.
    platform_id VARCHAR(255) NOT NULL,      -- Unique ID on that platform
    platform_url VARCHAR(500),              -- Profile/channel URL
    platform_username VARCHAR(255),         -- Username on that platform

    -- Platform-specific metadata (flexible JSONB)
    platform_metadata JSONB DEFAULT '{}',   -- Tier levels, subscriber count, etc.

    -- Platform-specific avatar (optional, overrides creator.avatar_filename)
    platform_avatar_url VARCHAR(500),       -- External URL (e.g., from YouTube API)

    -- Status
    is_active BOOLEAN DEFAULT true,         -- Whether to scrape this source
    scraper_enabled BOOLEAN DEFAULT true,   -- Per-source scraper control

    -- Scraping tracking
    last_scraped_at TIMESTAMP,
    last_scrape_status VARCHAR(50),         -- 'success', 'failed', 'partial'
    last_scrape_error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    UNIQUE(platform, platform_id)           -- One source per platform per creator
);

COMMENT ON TABLE creator_sources IS 'Platform-specific channels/accounts for each creator';
COMMENT ON COLUMN creator_sources.platform IS 'Platform identifier (patreon, youtube, substack, etc)';
COMMENT ON COLUMN creator_sources.platform_metadata IS 'Platform-specific data (JSONB for flexibility)';
COMMENT ON COLUMN creator_sources.platform_avatar_url IS 'Platform-specific avatar URL (optional, overrides creator avatar)';
COMMENT ON COLUMN creator_sources.is_active IS 'Whether this source should be scraped';

CREATE INDEX idx_creator_sources_creator ON creator_sources(creator_id);
CREATE INDEX idx_creator_sources_platform ON creator_sources(platform);
CREATE INDEX idx_creator_sources_active ON creator_sources(is_active) WHERE is_active = true;
CREATE INDEX idx_creator_sources_scraper ON creator_sources(scraper_enabled) WHERE scraper_enabled = true;

-- ============================================
-- POSTS: Content from all sources
-- ============================================
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES creator_sources(id) ON DELETE CASCADE,

    -- Post identification
    platform_post_id VARCHAR(255) NOT NULL,  -- Post ID on the platform
    title VARCHAR(1000) NOT NULL,
    content TEXT,
    content_blocks JSONB DEFAULT '[]',

    -- Timestamps
    published_at TIMESTAMP,

    -- URL
    post_url TEXT NOT NULL,

    -- Media counts
    image_count INTEGER DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    audio_count INTEGER DEFAULT 0,

    -- Search
    search_vector tsvector,
    embedding vector(1536),  -- For semantic search (OpenAI embeddings)

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    UNIQUE(source_id, platform_post_id)  -- No duplicate posts from same source
);

COMMENT ON TABLE posts IS 'Content posts from all sources (multi-platform)';
COMMENT ON COLUMN posts.source_id IS 'References creator_sources (not creators directly)';
COMMENT ON COLUMN posts.platform_post_id IS 'Post ID on the source platform';
COMMENT ON COLUMN posts.content_blocks IS 'Structured content blocks (text, images, videos, etc)';

CREATE INDEX idx_posts_source ON posts(source_id);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_tags ON posts USING gin(tags);
CREATE INDEX idx_posts_search ON posts USING gin(search_vector);
CREATE INDEX idx_posts_embedding ON posts USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- COLLECTIONS: Post groupings
-- ============================================
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES creator_sources(id) ON DELETE CASCADE,

    -- Collection identification
    collection_id VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    cover_image_url TEXT,

    post_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source_id, collection_id)  -- No duplicate collections per source
);

COMMENT ON TABLE collections IS 'Collections/playlists of posts (platform-specific)';

CREATE INDEX idx_collections_source ON collections(source_id);

-- Many-to-many: posts <-> collections
CREATE TABLE post_collections (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    position INTEGER,
    PRIMARY KEY (post_id, collection_id)
);

COMMENT ON TABLE post_collections IS 'Links posts to collections with ordering';

-- ============================================================================
-- MEDIA MANAGEMENT
-- ============================================================================

-- Media files with deduplication
CREATE TABLE media_files (
    id SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    file_type VARCHAR(20) NOT NULL,  -- 'image', 'video', 'audio'
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),

    -- Image specific
    width INTEGER,
    height INTEGER,

    -- Video/Audio specific
    duration FLOAT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Deduplication tracking
    reference_count INTEGER DEFAULT 0,
    first_seen_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE media_files IS 'Deduplicated media files storage';
COMMENT ON COLUMN media_files.file_hash IS 'SHA256 hash for deduplication';
COMMENT ON COLUMN media_files.reference_count IS 'Number of posts referencing this file';

CREATE INDEX idx_media_hash ON media_files(file_hash);
CREATE INDEX idx_media_type ON media_files(file_type);

-- Post-Media relationship
CREATE TABLE post_media (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    media_type VARCHAR(20),
    position INTEGER,
    caption TEXT,
    is_cover BOOLEAN DEFAULT false,

    UNIQUE (post_id, media_id, position)
);

COMMENT ON TABLE post_media IS 'Links media files to posts';

CREATE INDEX idx_post_media_post ON post_media(post_id);
CREATE INDEX idx_post_media_media ON post_media(media_id);

-- Transcriptions (audio/video)
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE UNIQUE,
    transcript_text TEXT NOT NULL,
    transcript_vtt TEXT,  -- WebVTT format with timestamps
    language VARCHAR(10),
    confidence_score FLOAT,
    transcribed_at TIMESTAMP DEFAULT NOW(),

    -- Search in transcriptions
    search_vector tsvector
);

COMMENT ON TABLE transcriptions IS 'Transcriptions of audio/video content';
COMMENT ON COLUMN transcriptions.transcript_vtt IS 'VTT format with timestamps for video players';

CREATE INDEX idx_transcriptions_search ON transcriptions USING gin(search_vector);

-- ============================================================================
-- SCRAPING STATUS (Replaces Firebase)
-- ============================================================================

CREATE TABLE scraping_status (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(255) NOT NULL,  -- platform_post_id (not DB id)
    source_id INTEGER NOT NULL REFERENCES creator_sources(id) ON DELETE CASCADE,
    post_url TEXT NOT NULL,

    -- Phase 1: URL Collection
    phase1_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    phase1_completed_at TIMESTAMP,
    phase1_attempts INTEGER DEFAULT 0,
    phase1_last_error TEXT,

    -- Phase 2: Detail Extraction
    phase2_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    phase2_completed_at TIMESTAMP,
    phase2_attempts INTEGER DEFAULT 0,
    phase2_last_error TEXT,

    -- Phase 3: Collections (optional)
    phase3_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed', 'skipped'
    phase3_completed_at TIMESTAMP,
    phase3_attempts INTEGER DEFAULT 0,
    phase3_last_error TEXT,

    -- Metadata from scraping
    has_images BOOLEAN DEFAULT false,
    has_videos BOOLEAN DEFAULT false,
    has_audio BOOLEAN DEFAULT false,

    -- Firebase migration fields (for data preservation)
    firebase_migrated BOOLEAN DEFAULT false,
    firebase_data JSONB,  -- Original Firebase data for reference

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source_id, post_id)  -- One status record per post per source
);

COMMENT ON TABLE scraping_status IS 'Tracks scraping status for each post (replaces Firebase)';
COMMENT ON COLUMN scraping_status.post_id IS 'Platform post ID (e.g., Patreon post ID)';
COMMENT ON COLUMN scraping_status.source_id IS 'Which source this post belongs to';
COMMENT ON COLUMN scraping_status.firebase_data IS 'Original Firebase data preserved during migration';

CREATE INDEX idx_scraping_status_source ON scraping_status(source_id);
CREATE INDEX idx_scraping_status_phase1 ON scraping_status(phase1_status) WHERE phase1_status = 'pending';
CREATE INDEX idx_scraping_status_phase2 ON scraping_status(phase2_status) WHERE phase2_status = 'pending';
CREATE INDEX idx_scraping_status_phase3 ON scraping_status(phase3_status) WHERE phase3_status = 'pending';

-- ============================================================================
-- USER MANAGEMENT
-- ============================================================================

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',  -- 'admin', 'user', 'readonly'

    -- 2FA
    totp_secret VARCHAR(32),
    totp_enabled BOOLEAN DEFAULT false,

    -- Profile
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',

    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

COMMENT ON TABLE users IS 'System users with authentication';
COMMENT ON COLUMN users.totp_secret IS 'TOTP secret for 2FA (encrypted)';

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(active) WHERE active = true;

-- User lists (for organizing posts)
CREATE TABLE user_lists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7),  -- Hex color
    position INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, name)
);

COMMENT ON TABLE user_lists IS 'User-created lists for organizing posts';

-- User post data (personalization)
CREATE TABLE user_post_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,

    -- Lists
    lists INTEGER[] DEFAULT '{}',  -- Array of list IDs

    -- Custom status
    status VARCHAR(50),  -- 'unread', 'in-progress', 'completed', custom

    -- Notes
    notes TEXT,

    -- Highlights
    highlights JSONB DEFAULT '[]',

    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, post_id)
);

COMMENT ON TABLE user_post_data IS 'User-specific data for posts (notes, status, lists)';

CREATE INDEX idx_user_post_data_user ON user_post_data(user_id);
CREATE INDEX idx_user_post_data_post ON user_post_data(post_id);

-- ============================================================================
-- JOB QUEUE
-- ============================================================================

-- Jobs table for Celery-like queue
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,  -- 'scrape_phase1', 'download_video', etc
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,

    -- Job data
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT,

    -- Retry logic
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP,

    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

COMMENT ON TABLE jobs IS 'Job queue for async processing';
COMMENT ON COLUMN jobs.payload IS 'JSON with job parameters';

CREATE INDEX idx_jobs_status_priority ON jobs(status, priority DESC, created_at);
CREATE INDEX idx_jobs_type ON jobs(job_type);

-- ============================================================================
-- SYSTEM CONFIGURATION
-- ============================================================================

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE system_config IS 'System-wide configuration key-value store';

-- Audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    changes JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE audit_log IS 'Audit trail for important system actions';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_creators_updated_at BEFORE UPDATE ON creators
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_creator_sources_updated_at BEFORE UPDATE ON creator_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_post_data_updated_at BEFORE UPDATE ON user_post_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraping_status_updated_at BEFORE UPDATE ON scraping_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-update search vector for posts
CREATE OR REPLACE FUNCTION posts_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('spanish', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.content, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_vector_trigger
BEFORE INSERT OR UPDATE OF title, content, tags ON posts
FOR EACH ROW EXECUTE FUNCTION posts_search_vector_update();

-- Auto-update search vector for transcriptions
CREATE OR REPLACE FUNCTION transcriptions_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('spanish', COALESCE(NEW.transcript_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER transcriptions_search_vector_trigger
BEFORE INSERT OR UPDATE OF transcript_text ON transcriptions
FOR EACH ROW EXECUTE FUNCTION transcriptions_search_vector_update();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Posts with full creator and source info
CREATE VIEW posts_with_details AS
SELECT
    p.*,
    cs.platform,
    cs.platform_username,
    cs.platform_url as source_url,
    cs.platform_avatar_url as source_avatar,
    c.id as creator_db_id,
    c.name as creator_name,
    c.display_name as creator_display_name,
    c.avatar_filename as creator_avatar_filename,
    c.website_url as creator_website
FROM posts p
JOIN creator_sources cs ON cs.id = p.source_id
JOIN creators c ON c.id = cs.creator_id;

COMMENT ON VIEW posts_with_details IS 'Posts with full creator and source information';

-- View: Creator summary with source counts
CREATE VIEW creator_summary AS
SELECT
    c.*,
    COUNT(DISTINCT cs.id) as source_count,
    COUNT(DISTINCT p.id) as total_posts,
    ARRAY_AGG(DISTINCT cs.platform) as platforms
FROM creators c
LEFT JOIN creator_sources cs ON cs.creator_id = c.id
LEFT JOIN posts p ON p.source_id = cs.id
GROUP BY c.id;

COMMENT ON VIEW creator_summary IS 'Creator summary with source and post counts';

-- View: Media with usage count
CREATE VIEW media_usage AS
SELECT
    mf.*,
    COUNT(pm.id) as usage_count
FROM media_files mf
LEFT JOIN post_media pm ON pm.media_id = mf.id
GROUP BY mf.id;

COMMENT ON VIEW media_usage IS 'Media files with actual usage count';

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default system config
INSERT INTO system_config (key, value, description) VALUES
('version', '"2.0"', 'Database schema version'),
('scraper_enabled', 'true', 'Global scraper enable/disable'),
('max_concurrent_jobs', '5', 'Maximum concurrent jobs'),
('default_retry_delay', '300', 'Default retry delay in seconds'),
('multi_source_enabled', 'true', 'Multi-source schema enabled (v2)');

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant permissions to patreon_user (adjust if different user)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO patreon_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO patreon_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO patreon_user;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
    RAISE NOTICE '║  ✅ Schema V2 Created Successfully!                        ║';
    RAISE NOTICE '╠════════════════════════════════════════════════════════════╣';
    RAISE NOTICE '║  Multi-Source Design Features:                             ║';
    RAISE NOTICE '║  • Creators (entities) separated from Sources (platforms)  ║';
    RAISE NOTICE '║  • One creator can have multiple sources                   ║';
    RAISE NOTICE '║  • Supports Patreon, YouTube, Substack, and more          ║';
    RAISE NOTICE '╠════════════════════════════════════════════════════════════╣';
    RAISE NOTICE '║  Tables: %                                               ║', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE');
    RAISE NOTICE '║  Views: %                                                ║', (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public');
    RAISE NOTICE '║  Indexes: %                                              ║', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
    RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    RAISE NOTICE '';
END $$;
