#!/bin/bash
# STEP 1: Backup database before migration
# Safe to run multiple times - creates timestamped backups

set -e  # Exit on error

echo "========================================="
echo "  STEP 1: Database Backup"
echo "========================================="
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set defaults
DB_USER=${DB_USER:-patreon_user}
DB_NAME=${DB_NAME:-alejandria}
DB_HOST=${DB_HOST:-127.0.0.1}

# Create backup directory
BACKUP_DIR="backups/schema_v2_migration"
mkdir -p "$BACKUP_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/alejandria_before_v2_migration_${TIMESTAMP}.sql"

echo "📦 Creating backup..."
echo "   Database: $DB_NAME"
echo "   File: $BACKUP_FILE"
echo ""

# Create backup
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    -f "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup created successfully!"
    echo ""
    echo "Backup details:"
    ls -lh "$BACKUP_FILE"
    echo ""
    echo "File size: $(du -h "$BACKUP_FILE" | cut -f1)"
    echo ""
    echo "========================================="
    echo "  BACKUP COMPLETE - Safe to proceed"
    echo "========================================="
    echo ""
    echo "If anything goes wrong, restore with:"
    echo "  PGPASSWORD=\$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
    echo ""
else
    echo "❌ Backup failed!"
    exit 1
fi
