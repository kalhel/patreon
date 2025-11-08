-- ============================================================================
-- Patreon Scraper - PostgreSQL Database Schema
-- ============================================================================
-- Version: 1.0
-- Date: 2025-11-07
-- Description: Complete database schema for the patreon scraper system
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- CORE ENTITIES
-- ============================================================================

-- Creators table
CREATE TABLE creators (
    id SERIAL PRIMARY KEY,
    creator_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    patreon_url TEXT,
    active BOOLEAN DEFAULT true,
    scraper_enabled BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE creators IS 'Content creators from Patreon and other sources';
COMMENT ON COLUMN creators.creator_id IS 'Unique identifier from the source platform';
COMMENT ON COLUMN creators.scraper_enabled IS 'Whether to include this creator in automated scraping';

-- Collections table
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    collection_id VARCHAR(100) UNIQUE NOT NULL,
    creator_id INTEGER REFERENCES creators(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    cover_image_url TEXT,
    post_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE collections IS 'Collections/playlists of posts';

-- Posts table
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(100) UNIQUE NOT NULL,
    creator_id INTEGER REFERENCES creators(id) ON DELETE CASCADE,
    title VARCHAR(1000) NOT NULL,
    content TEXT,
    content_blocks JSONB DEFAULT '[]',
    published_at TIMESTAMP,
    patreon_url TEXT,

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
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE posts IS 'Content posts from all sources';
COMMENT ON COLUMN posts.content_blocks IS 'Structured content blocks (text, images, videos, etc)';
COMMENT ON COLUMN posts.search_vector IS 'Full-text search vector (auto-updated)';
COMMENT ON COLUMN posts.embedding IS 'Vector embedding for semantic search';

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

-- ============================================================================
-- SCRAPING STATUS (Replaces Firebase)
-- ============================================================================

-- Scraping status tracking (replaces Firebase)
CREATE TABLE scraping_status (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(100) UNIQUE NOT NULL,
    creator_id INTEGER REFERENCES creators(id) ON DELETE CASCADE,
    post_url TEXT NOT NULL,

    -- Status tracking
    phase1_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    phase1_completed_at TIMESTAMP,

    phase2_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
    phase2_completed_at TIMESTAMP,
    phase2_attempts INTEGER DEFAULT 0,
    phase2_last_error TEXT,

    -- Metadata from scraping
    has_images BOOLEAN DEFAULT false,
    has_videos BOOLEAN DEFAULT false,
    has_audio BOOLEAN DEFAULT false,

    -- Firebase migration fields
    firebase_migrated BOOLEAN DEFAULT false,
    firebase_data JSONB,  -- Original Firebase data for reference

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE scraping_status IS 'Tracks scraping status for each post (replaces Firebase)';
COMMENT ON COLUMN scraping_status.phase1_status IS 'URL collection status';
COMMENT ON COLUMN scraping_status.phase2_status IS 'Detail extraction status';
COMMENT ON COLUMN scraping_status.firebase_data IS 'Original Firebase data preserved during migration';

CREATE INDEX idx_scraping_status_creator ON scraping_status(creator_id);
CREATE INDEX idx_scraping_status_phase2 ON scraping_status(phase2_status) WHERE phase2_status = 'pending';

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
-- INDEXES
-- ============================================================================

-- Creator indexes
CREATE INDEX idx_creators_active ON creators(active) WHERE active = true;

-- Post indexes
CREATE INDEX idx_posts_creator ON posts(creator_id);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_tags ON posts USING gin(tags);
CREATE INDEX idx_posts_search ON posts USING gin(search_vector);
CREATE INDEX idx_posts_embedding ON posts USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- Media indexes
CREATE INDEX idx_media_hash ON media_files(file_hash);
CREATE INDEX idx_media_type ON media_files(file_type);
CREATE INDEX idx_post_media_post ON post_media(post_id);
CREATE INDEX idx_post_media_media ON post_media(media_id);

-- Transcription indexes
CREATE INDEX idx_transcriptions_search ON transcriptions USING gin(search_vector);

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(active) WHERE active = true;
CREATE INDEX idx_user_post_data_user ON user_post_data(user_id);
CREATE INDEX idx_user_post_data_post ON user_post_data(post_id);

-- Job indexes
CREATE INDEX idx_jobs_status_priority ON jobs(status, priority DESC, created_at);
CREATE INDEX idx_jobs_type ON jobs(job_type);

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

-- View: Posts with creator info
CREATE VIEW posts_with_creators AS
SELECT
    p.*,
    c.name as creator_name,
    c.avatar_url as creator_avatar,
    c.creator_id as creator_platform_id
FROM posts p
JOIN creators c ON c.id = p.creator_id;

COMMENT ON VIEW posts_with_creators IS 'Posts joined with creator information';

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
('version', '"1.0"', 'Database schema version'),
('scraper_enabled', 'true', 'Global scraper enable/disable'),
('max_concurrent_jobs', '5', 'Maximum concurrent jobs'),
('default_retry_delay', '300', 'Default retry delay in seconds');

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
    RAISE NOTICE '✅ Schema created successfully!';
    RAISE NOTICE 'Tables: % ', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE');
    RAISE NOTICE 'Views: % ', (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public');
    RAISE NOTICE 'Indexes: % ', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
END $$;
