-- ============================================================================
-- ROLLBACK: Remove Legacy V1 Column Documentation
-- ============================================================================
-- Date: 2025-11-09
-- Purpose: Rollback migration 2025-11-09_document_legacy_v1_columns.sql
--
-- This script removes all COMMENT documentation added to legacy columns.
-- Use this if you need to revert the documentation changes.
--
-- WARNING: This only removes documentation, not the columns themselves.
-- ============================================================================

-- Set search path
SET search_path TO public;

-- ============================================================================
-- Remove all column comments
-- ============================================================================

COMMENT ON COLUMN posts.creator_id IS NULL;
COMMENT ON COLUMN posts.creator_name IS NULL;
COMMENT ON COLUMN posts.creator_avatar IS NULL;
COMMENT ON COLUMN posts.patreon_tags IS NULL;
COMMENT ON COLUMN posts.source_id IS NULL;

-- ============================================================================
-- Verification
-- ============================================================================
\echo '✅ All column comments removed (rollback complete)'
\echo ''
\echo '📝 To verify comments are removed:'
\echo 'SELECT'
\echo '    column_name,'
\echo '    col_description(''posts''::regclass, ordinal_position) as description'
\echo 'FROM information_schema.columns'
\echo 'WHERE table_name = ''posts'''
\echo '  AND column_name IN (''creator_id'', ''creator_name'', ''creator_avatar'', ''patreon_tags'', ''source_id'');'
