#!/bin/bash
# Test PostgreSQL connection with credentials from .env

echo "============================================================"
echo "  Testing PostgreSQL Connection"
echo "============================================================"
echo ""

# Source .env
source .env

echo "Testing connection with:"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo ""

# Test with psql
echo "Test 1: psql connection..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ psql connection successful"
else
    echo "❌ psql connection failed"
fi

echo ""

# Test with pg_dump
echo "Test 2: pg_dump (dry run)..."
PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --schema-only -f /tmp/test_dump.sql 2>&1

if [ $? -eq 0 ]; then
    echo "✅ pg_dump successful"
    rm -f /tmp/test_dump.sql
else
    echo "❌ pg_dump failed"
fi

echo ""
echo "============================================================"
