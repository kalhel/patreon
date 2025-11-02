#!/bin/bash
#
# Daily Scrape Script for Patreon Content
# Runs incrementally - only scrapes new posts
#
# Usage:
#   ./daily_scrape.sh [--full-details] [--with-media] [--with-tags] [--with-notion]
#
# Options:
#   --full-details  : Scrape full post details (slower but complete)
#   --with-media    : Download media files after scraping
#   --with-tags     : Generate tags with AI after scraping
#   --with-notion   : Upload to Notion after processing
#   --all           : Do everything (scrape, media, tags, notion)
#
# Examples:
#   ./daily_scrape.sh                              # Quick scrape only
#   ./daily_scrape.sh --full-details               # Scrape with details
#   ./daily_scrape.sh --all                        # Complete pipeline
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/home/javif/proyectos/astrologia/patreon"
cd "$PROJECT_DIR"

# Activate virtual environment
source venv/bin/activate

# Parse arguments
FULL_DETAILS=""
WITH_MEDIA=false
WITH_TAGS=false
WITH_NOTION=false

for arg in "$@"; do
    case $arg in
        --full-details)
            FULL_DETAILS="--full-details"
            ;;
        --with-media)
            WITH_MEDIA=true
            ;;
        --with-tags)
            WITH_TAGS=true
            ;;
        --with-notion)
            WITH_NOTION=true
            ;;
        --all)
            FULL_DETAILS="--full-details"
            WITH_MEDIA=true
            WITH_TAGS=true
            WITH_NOTION=true
            ;;
    esac
done

# Log file
LOG_FILE="logs/daily_scrape_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Daily Patreon Scrape${NC}"
echo -e "${BLUE}  $(date)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to log and display
log_step() {
    echo -e "${GREEN}▶ $1${NC}"
    echo "▶ $1" >> "$LOG_FILE"
}

log_info() {
    echo -e "${YELLOW}  $1${NC}"
    echo "  $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
    echo "✗ $1" >> "$LOG_FILE"
}

# Step 1: Incremental Scrape
log_step "Step 1: Incremental Scraping"
log_info "Checking for new posts..."

if python src/incremental_scraper.py --scrape-all $FULL_DETAILS --headless 2>&1 | tee -a "$LOG_FILE"; then
    log_info "✓ Scraping complete"

    # Check if there were new posts
    NEW_POSTS=$(grep -c "NEW:" "$LOG_FILE" || echo "0")

    if [ "$NEW_POSTS" -eq 0 ]; then
        log_info "No new posts found. Everything is up to date!"
        echo ""
        echo -e "${GREEN}✅ All done! No new content.${NC}"
        exit 0
    fi

    log_info "Found $NEW_POSTS new posts!"
else
    log_error "Scraping failed"
    exit 1
fi

echo ""

# Step 2: Download Media (if requested and there were new posts)
if [ "$WITH_MEDIA" = true ]; then
    log_step "Step 2: Downloading Media"

    if python src/media_downloader.py --all 2>&1 | tee -a "$LOG_FILE"; then
        log_info "✓ Media download complete"
    else
        log_error "Media download failed"
        exit 1
    fi

    echo ""
fi

# Step 3: Generate Tags (if requested and there were new posts)
if [ "$WITH_TAGS" = true ]; then
    log_step "Step 3: Generating Tags"

    # Check if GEMINI_API_KEY is set
    if [ -z "$GEMINI_API_KEY" ]; then
        log_error "GEMINI_API_KEY not set. Skipping tag generation."
    else
        if python src/tag_generator.py --all 2>&1 | tee -a "$LOG_FILE"; then
            log_info "✓ Tag generation complete"
        else
            log_error "Tag generation failed"
            exit 1
        fi
    fi

    echo ""
fi

# Step 4: Upload to Notion (if requested and there were new posts)
if [ "$WITH_NOTION" = true ]; then
    log_step "Step 4: Uploading to Notion"

    # Check if NOTION_API_KEY is set
    if [ -z "$NOTION_API_KEY" ]; then
        log_error "NOTION_API_KEY not set. Skipping Notion upload."
    else
        if python src/notion_integrator.py --all 2>&1 | tee -a "$LOG_FILE"; then
            log_info "✓ Notion upload complete"
        else
            log_error "Notion upload failed"
            exit 1
        fi
    fi

    echo ""
fi

# Summary
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ Daily scrape complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "📊 Summary:"
echo -e "   New posts: ${GREEN}$NEW_POSTS${NC}"
echo -e "   Log file: ${BLUE}$LOG_FILE${NC}"
echo ""

# Send notification (optional - uncomment if you want notifications)
# notify-send "Patreon Scraper" "Found $NEW_POSTS new posts"

exit 0
