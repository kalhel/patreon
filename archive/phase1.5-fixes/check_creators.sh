#!/bin/bash
# Check how many creators we have

source .env

echo "============================================================"
echo "  Checking Creators in Database"
echo "============================================================"
echo ""

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'

\echo '--- CREATORS ---'
SELECT id, name, avatar_filename FROM creators ORDER BY id;

\echo ''
\echo '--- CREATOR_SOURCES ---'
SELECT cs.id, c.name, cs.platform, cs.platform_id
FROM creator_sources cs
JOIN creators c ON c.id = cs.creator_id
ORDER BY c.name, cs.platform;

\echo ''
\echo '--- COUNTS ---'
SELECT
    (SELECT COUNT(*) FROM creators) as total_creators,
    (SELECT COUNT(*) FROM creator_sources) as total_sources,
    (SELECT COUNT(*) FROM scraping_status) as total_scraping_status;

EOF

echo ""
echo "============================================================"
