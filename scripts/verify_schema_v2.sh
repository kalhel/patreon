#!/bin/bash
# Verify Schema V2 Migration Success

source .env

echo "============================================================"
echo "  Schema V2 Migration Verification"
echo "============================================================"
echo ""

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'

\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  1. Schema V2 Tables Verification'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'creator_sources')
        THEN '✅ creator_sources table exists (v2 indicator)'
        ELSE '❌ creator_sources table missing'
    END as check_v2;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  2. Data Migration Verification'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT
    c.id as creator_id,
    c.name as creator_name,
    cs.platform,
    cs.platform_id,
    COUNT(ss.id) as urls_to_scrape,
    CASE
        WHEN COUNT(ss.id) > 0 THEN '✅'
        ELSE '❌'
    END as status
FROM creators c
JOIN creator_sources cs ON cs.creator_id = c.id
LEFT JOIN scraping_status ss ON ss.source_id = cs.id
GROUP BY c.id, c.name, cs.platform, cs.platform_id
ORDER BY c.name;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  3. Table Counts Summary'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT
    'creators' as table_name,
    COUNT(*) as count,
    '✅' as status
FROM creators
UNION ALL
SELECT
    'creator_sources',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM creator_sources
UNION ALL
SELECT
    'scraping_status',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM scraping_status
UNION ALL
SELECT
    'posts',
    COUNT(*),
    '⏳ (will be filled by scraper)'
FROM posts;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  4. Multi-Source Capability Check'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'creator_sources' AND column_name = 'platform'
        )
        THEN '✅ Multi-source design: One creator can have multiple platforms'
        ELSE '❌ Multi-source design not implemented'
    END as multi_source_check;

\echo ''
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo '  ✅ Schema V2 Migration Verification Complete'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
\echo ''

EOF

echo ""
echo "============================================================"
echo "Next Steps:"
echo "  • Phase 2: Implement PostgresTracker"
echo "  • Update scraper to use new multi-source schema"
echo "  • Add more creators and platforms"
echo "============================================================"
