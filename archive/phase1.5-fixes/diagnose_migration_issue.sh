#!/bin/bash
# Diagnose what happened during migration - check Firebase data

source .env

echo "============================================================"
echo "  Diagnosing Migration Issue - Checking Creator Data"
echo "============================================================"
echo ""

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'

\echo '--- SAMPLE: Firebase data in scraping_status (first 10 posts) ---'
SELECT
    post_id,
    firebase_data->>'creator_id' as creator_from_firebase,
    firebase_data->>'url' as url_from_firebase
FROM scraping_status
LIMIT 10;

\echo ''
\echo '--- CREATOR DISTRIBUTION in Firebase data ---'
SELECT
    firebase_data->>'creator_id' as creator_id,
    COUNT(*) as post_count
FROM scraping_status
GROUP BY firebase_data->>'creator_id'
ORDER BY post_count DESC;

\echo ''
\echo '--- Check if Firebase data is NULL ---'
SELECT
    COUNT(*) as total_posts,
    COUNT(firebase_data) as posts_with_firebase_data,
    COUNT(*) - COUNT(firebase_data) as posts_missing_firebase_data
FROM scraping_status;

EOF

echo ""
echo "============================================================"
