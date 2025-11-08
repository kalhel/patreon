#!/bin/bash
# Restore the oldest backup (the first v1 schema backup before migration attempts)

# Load environment variables
source .env

echo "============================================================"
echo "  Restore Oldest V1 Schema Backup"
echo "============================================================"
echo ""

# Find the oldest backup (first one created)
BACKUP_FILE=$(ls -t database/backups/schema_v1_backup_*.sql 2>/dev/null | tail -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ No backup files found in database/backups/"
    exit 1
fi

echo "Restoring from: $BACKUP_FILE"
echo ""
echo "This will:"
echo "  1. Drop all existing tables"
echo "  2. Restore schema v1 from oldest backup"
echo "  3. Ready for migration to v2"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Restoring database..."

# Restore using psql
PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored from oldest backup!"
    echo ""
    echo "Next step: Run the migration"
    echo "  python scripts/migrate_to_schema_v2.py"
else
    echo ""
    echo "❌ Restore failed!"
    exit 1
fi
