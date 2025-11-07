#!/bin/bash
# Restore the most recent backup

source .env

echo "============================================================"
echo "  EMERGENCY RESTORE - Most Recent Backup"
echo "============================================================"
echo ""

# Find the most recent backup
BACKUP_FILE=$(ls -t database/backups/schema_v1_backup_*.sql 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ No backup files found in database/backups/"
    exit 1
fi

echo "Most recent backup: $BACKUP_FILE"
echo ""
echo "This will RESTORE the database to the backup state"
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
    echo "✅ Database restored!"
else
    echo ""
    echo "❌ Restore failed!"
    exit 1
fi
