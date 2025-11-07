-- =====================================================
-- FIX: Drop old posts table and recreate with correct schema
-- =====================================================

-- Drop old table if it has wrong structure
DROP TABLE IF EXISTS post_collections CASCADE;
DROP TABLE IF EXISTS posts CASCADE;

-- Now the schema_posts.sql can be applied cleanly
-- Run this first, then run: python src/migrate_json_to_postgres.py --schema-only
