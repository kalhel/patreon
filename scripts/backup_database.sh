#!/bin/bash
# ==============================================================================
# Database Backup Script
# ==============================================================================
# Creates a timestamped backup of the PostgreSQL database
# Usage: ./scripts/backup_database.sh [output_dir]
# ==============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${1:-$PROJECT_ROOT/database/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/patreon_backup_${TIMESTAMP}.sql"

# Load .env for database credentials
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Extract database connection info from DATABASE_URL
# Format: postgresql://user:pass@host:port/dbname
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ ERROR: DATABASE_URL not set in .env${NC}"
    exit 1
fi

# Parse DATABASE_URL
DB_USER=$(echo "$DATABASE_URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

# Default to localhost:5432 if not specified
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"

echo "============================================================"
echo "  PostgreSQL Database Backup"
echo "============================================================"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST:$DB_PORT"
echo "  User: $DB_USER"
echo "  Output: $BACKUP_FILE"
echo "============================================================"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Run pg_dump
echo -e "${YELLOW}Creating backup...${NC}"
export PGPASSWORD="$DB_PASS"

pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$BACKUP_FILE" \
    --clean \
    --if-exists \
    --verbose

if [ $? -eq 0 ]; then
    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

    echo ""
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $FILE_SIZE"
    echo ""

    # Compress backup (optional)
    read -p "Compress backup with gzip? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Compressing...${NC}"
        gzip "$BACKUP_FILE"
        COMPRESSED_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        echo -e "${GREEN}✅ Compressed: $COMPRESSED_FILE ($COMPRESSED_SIZE)${NC}"
    fi

    # Clean old backups (keep last 10)
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/patreon_backup_*.sql* 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 10 ]; then
        echo ""
        echo -e "${YELLOW}Found $BACKUP_COUNT backups. Cleaning old backups (keeping last 10)...${NC}"
        ls -1t "$BACKUP_DIR"/patreon_backup_*.sql* | tail -n +11 | xargs rm -f
        echo -e "${GREEN}✅ Cleanup complete${NC}"
    fi

else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Unset password
unset PGPASSWORD

echo ""
echo "============================================================"
echo "  To restore this backup:"
echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $BACKUP_FILE"
echo "============================================================"
