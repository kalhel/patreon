#!/bin/bash
# Diagnose current database state

source .env

echo "============================================================"
echo "  Database State Diagnostic"
echo "============================================================"
echo ""

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'

-- Check what tables exist
\echo '--- TABLES ---'
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

\echo ''
\echo '--- TABLE COUNTS ---'
SELECT
    'creators' as table_name,
    COUNT(*) as count
FROM creators
UNION ALL
SELECT
    'creator_sources',
    COUNT(*)
FROM creator_sources
UNION ALL
SELECT
    'scraping_status',
    COUNT(*)
FROM scraping_status
UNION ALL
SELECT
    'posts',
    COUNT(*)
FROM posts;

\echo ''
\echo '--- CREATOR_SOURCES COLUMNS (v2 indicator) ---'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'creator_sources'
ORDER BY ordinal_position;

EOF

echo ""
echo "============================================================"
