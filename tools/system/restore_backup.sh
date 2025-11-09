#!/bin/bash
# Restore database from backup

# Load environment variables
source .env

echo "============================================================"
echo "  Restore Database Backup"
echo "============================================================"
echo ""

# Find the most recent backup
BACKUP_FILE=$(ls -t database/backups/schema_v1_backup_*.sql 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ No backup files found in database/backups/"
    exit 1
fi

echo "Found backup: $BACKUP_FILE"
echo ""
echo "This will:"
echo "  1. Drop all existing tables"
echo "  2. Restore from backup"
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
    echo "✅ Database restored successfully!"
    echo ""
    echo "Next step: Run the migration again"
    echo "  python scripts/migrate_to_schema_v2.py"
else
    echo ""
    echo "❌ Restore failed!"
    exit 1
fi
