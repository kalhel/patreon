#!/bin/bash
# ============================================================================
# Phase 0 Setup Script - Infrastructure Installation
# ============================================================================
# This script guides you through installing PostgreSQL, Redis, and dependencies
# Run with: bash scripts/setup_phase0.sh
# ============================================================================

set -e  # Exit on error

echo "============================================================"
echo "🚀 Phase 0 Setup - Infrastructure Installation"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Helper functions
# ============================================================================

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "ℹ️  $1"
}

prompt() {
    read -p "$(echo -e ${YELLOW}$1${NC}) " response
    echo $response
}

# ============================================================================
# Check if running on Linux
# ============================================================================

if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "This script is designed for Linux systems"
    exit 1
fi

info "Detected OS: $(lsb_release -d | cut -f2)"
echo ""

# ============================================================================
# Step 1: Update system
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Step 1: Update system packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $(prompt "Update system packages? (y/n)") == "y" ]]; then
    sudo apt update && sudo apt upgrade -y
    success "System updated"
else
    warning "Skipping system update"
fi
echo ""

# ============================================================================
# Step 2: Install PostgreSQL
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐘 Step 2: Install PostgreSQL 15+"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v psql &> /dev/null; then
    PG_VERSION=$(psql --version | awk '{print $3}')
    success "PostgreSQL already installed: $PG_VERSION"
else
    if [[ $(prompt "Install PostgreSQL? (y/n)") == "y" ]]; then
        sudo apt install -y postgresql postgresql-contrib
        success "PostgreSQL installed"
    else
        error "PostgreSQL is required. Exiting."
        exit 1
    fi
fi
echo ""

# ============================================================================
# Step 3: Install pgvector extension
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔢 Step 3: Install pgvector extension"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Try to install from package
if apt-cache search postgresql-.*-pgvector | grep -q pgvector; then
    if [[ $(prompt "Install pgvector from apt? (y/n)") == "y" ]]; then
        sudo apt install -y postgresql-15-pgvector || sudo apt install -y postgresql-14-pgvector
        success "pgvector installed"
    fi
else
    warning "pgvector not found in apt repositories"
    info "You may need to compile from source: https://github.com/pgvector/pgvector"
    info "Or use Docker (see docker-compose.yml)"
fi
echo ""

# ============================================================================
# Step 4: Configure PostgreSQL
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  Step 4: Configure PostgreSQL database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $(prompt "Create database and user? (y/n)") == "y" ]]; then
    echo ""
    info "Creating database 'patreon' and user 'patreon_user'"

    # Generate random password if not set
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    sudo -u postgres psql <<EOF
-- Create user
CREATE USER patreon_user WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE patreon OWNER patreon_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE patreon TO patreon_user;

-- Connect to patreon database
\c patreon

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO patreon_user;

\q
EOF

    success "Database configured"
    info "Database: patreon"
    info "User: patreon_user"
    warning "Password: $DB_PASSWORD"
    warning "SAVE THIS PASSWORD! Add it to your .env file"

    # Save to .env
    if [[ ! -f .env ]]; then
        cp .env.example .env 2>/dev/null || touch .env
    fi

    echo ""
    echo "DB_NAME=patreon" >> .env
    echo "DB_USER=patreon_user" >> .env
    echo "DB_PASSWORD=$DB_PASSWORD" >> .env
    echo "DB_HOST=localhost" >> .env
    echo "DB_PORT=5432" >> .env

    success "Credentials saved to .env"
else
    warning "Skipping database creation"
fi
echo ""

# ============================================================================
# Step 5: Run schema.sql
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Step 5: Create database schema"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -f database/schema.sql ]]; then
    if [[ $(prompt "Run database/schema.sql? (y/n)") == "y" ]]; then
        PGPASSWORD=$DB_PASSWORD psql -U patreon_user -d patreon -h localhost -f database/schema.sql
        success "Schema created"
    else
        warning "Skipping schema creation"
    fi
else
    error "database/schema.sql not found"
fi
echo ""

# ============================================================================
# Step 6: Install Redis
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔴 Step 6: Install Redis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v redis-cli &> /dev/null; then
    REDIS_VERSION=$(redis-cli --version | awk '{print $2}')
    success "Redis already installed: $REDIS_VERSION"
else
    if [[ $(prompt "Install Redis? (y/n)") == "y" ]]; then
        sudo apt install -y redis-server
        success "Redis installed"
    else
        error "Redis is required. Exiting."
        exit 1
    fi
fi

# Start Redis
if systemctl is-active --quiet redis-server; then
    success "Redis is running"
else
    info "Starting Redis..."
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    success "Redis started and enabled"
fi

# Save Redis config to .env
if [[ ! -f .env ]]; then
    touch .env
fi
echo "REDIS_HOST=localhost" >> .env
echo "REDIS_PORT=6379" >> .env

echo ""

# ============================================================================
# Step 7: Install Python dependencies
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Step 7: Install Python dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -d venv ]]; then
    info "Virtual environment exists"
else
    info "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

if [[ $(prompt "Install/update Python packages? (y/n)") == "y" ]]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    success "Python packages installed"
else
    warning "Skipping Python packages"
fi
echo ""

# ============================================================================
# Step 8: Test connections
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Step 8: Test connections"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ -f scripts/test_connections.py ]]; then
    python3 scripts/test_connections.py
else
    warning "scripts/test_connections.py not found"
fi
echo ""

# ============================================================================
# Complete
# ============================================================================

echo "============================================================"
echo "🎉 Phase 0 Setup Complete!"
echo "============================================================"
echo ""
success "Next steps:"
echo "  1. Review PROGRESS.md and mark completed tasks"
echo "  2. Check .env file for database credentials"
echo "  3. Run: python3 scripts/test_connections.py"
echo "  4. Start Phase 1: Data Migration"
echo ""
warning "Don't forget to backup your current data:"
echo "  tar -czf backup_jsons_\$(date +%Y%m%d).tar.gz data/"
echo ""
