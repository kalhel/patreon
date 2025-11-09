-- ============================================================================
-- Migration: Document Legacy V1 Columns as DEPRECATED
-- ============================================================================
-- Date: 2025-11-09
-- Author: Javi + Claude
-- Context: Schema V2 (multi-source) migration
--
-- Purpose:
--   Mark legacy V1 columns as DEPRECATED to guide future development.
--   These columns were kept for backward compatibility but should not be
--   used in new code.
--
-- Legacy V1 Columns (pre multi-source):
--   - creator_id (VARCHAR)     → Use source_id JOIN instead
--   - creator_name (VARCHAR)   → Use source_id JOIN to creators.name
--   - creator_avatar (TEXT)    → Use source_id JOIN to creators.avatar_filename
--   - patreon_tags (TEXT[])    → Should be renamed to 'tags' (platform-agnostic)
--
-- V2 Columns (current):
--   - source_id (INTEGER)      → FK to creator_sources (multi-platform)
--
-- Rollback: See 2025-11-09_rollback_legacy_documentation.sql
-- ============================================================================

-- Set search path
SET search_path TO public;

-- ============================================================================
-- 1. Document legacy creator_id column
-- ============================================================================
COMMENT ON COLUMN posts.creator_id IS
'DEPRECATED (V1): Legacy string identifier like "headonhistory", "astrobymax".
USE INSTEAD: source_id (FK to creator_sources) for multi-platform support.
Migration path: JOIN creator_sources cs ON p.source_id = cs.id → cs.platform_id
Kept for backward compatibility. Will be removed in future version.
Deprecated: 2025-11-09';

-- ============================================================================
-- 2. Document legacy creator_name column
-- ============================================================================
COMMENT ON COLUMN posts.creator_name IS
'DEPRECATED (V1): Denormalized creator name like "Ali A Olomi", "AstroByMax".
USE INSTEAD: source_id JOIN to creators.name
Migration path:
  JOIN creator_sources cs ON p.source_id = cs.id
  JOIN creators c ON cs.creator_id = c.id → c.name
Kept for backward compatibility. Will be removed in future version.
Deprecated: 2025-11-09';

-- ============================================================================
-- 3. Document legacy creator_avatar column
-- ============================================================================
COMMENT ON COLUMN posts.creator_avatar IS
'DEPRECATED (V1): Legacy avatar URL/path. No longer populated as of 2025-11-09.
USE INSTEAD: source_id JOIN to creators.avatar_filename
Migration path:
  JOIN creator_sources cs ON p.source_id = cs.id
  JOIN creators c ON cs.creator_id = c.id → c.avatar_filename
Stopped populating: 2025-11-09
Will be removed in future version.';

-- ============================================================================
-- 4. Document patreon_tags as platform-specific (should be generic 'tags')
-- ============================================================================
COMMENT ON COLUMN posts.patreon_tags IS
'PLATFORM-SPECIFIC: Should be renamed to "tags" for multi-platform support.
Current: patreon_tags (Patreon-specific naming)
Should be: tags (works for Patreon, YouTube, blogs, etc)
Planned rename: Future migration will rename patreon_tags → tags
Note: Functionally correct, just naming is platform-specific.';

-- ============================================================================
-- 5. Document source_id as the V2 standard
-- ============================================================================
COMMENT ON COLUMN posts.source_id IS
'V2 STANDARD: Foreign key to creator_sources (multi-platform design).
This is the correct way to link posts to creators across platforms.
Schema: posts.source_id → creator_sources.id → creators.id
Supports: Patreon, YouTube, blogs, books, etc.
Introduced: Schema V2 (2024)';

-- ============================================================================
-- Verification
-- ============================================================================
\echo '✅ Legacy V1 columns documented as DEPRECATED'
\echo '✅ source_id documented as V2 standard'
\echo ''
\echo '📊 Current state:'

SELECT
    COUNT(*) as total_posts,
    COUNT(source_id) as has_source_id_v2,
    COUNT(creator_id) as has_creator_id_v1,
    COUNT(creator_name) as has_creator_name_v1
FROM posts
WHERE deleted_at IS NULL;

\echo ''
\echo '📝 To view column comments:'
\echo 'SELECT'
\echo '    column_name,'
\echo '    col_description(''posts''::regclass, ordinal_position) as description'
\echo 'FROM information_schema.columns'
\echo 'WHERE table_name = ''posts'''
\echo '  AND column_name IN (''creator_id'', ''creator_name'', ''creator_avatar'', ''patreon_tags'', ''source_id'');'
