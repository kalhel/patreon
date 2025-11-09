#!/bin/bash
# Start Web Viewer with Gunicorn (Production Mode)
# Usage: ./scripts/start_web_viewer.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Patreon Web Viewer (Production Mode)${NC}"
echo ""

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}✓${NC} Activating virtual environment..."
source venv/bin/activate

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not installed. Installing..."
    pip3 install -r requirements.txt
fi

# Configuration
HOST="${WEB_VIEWER_HOST:-127.0.0.1}"
PORT="${WEB_VIEWER_PORT:-5001}"
WORKERS="${WEB_VIEWER_WORKERS:-4}"
TIMEOUT="${WEB_VIEWER_TIMEOUT:-120}"
LOG_LEVEL="${WEB_VIEWER_LOG_LEVEL:-info}"

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Host:     $HOST"
echo "  Port:     $PORT"
echo "  Workers:  $WORKERS"
echo "  Timeout:  ${TIMEOUT}s"
echo "  Log Level: $LOG_LEVEL"
echo ""
echo -e "${BLUE}📊 Access web viewer at: http://$HOST:$PORT${NC}"
echo ""

# Start gunicorn
exec gunicorn \
    --bind "$HOST:$PORT" \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --log-level "$LOG_LEVEL" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    web.viewer:app
