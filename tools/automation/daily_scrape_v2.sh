#!/bin/bash
#
# Daily Scrape Script V2 - Two-Phase Workflow with Firebase
# Phase 1: Collect URLs
# Phase 2: Extract details
#
# Usage:
#   ./daily_scrape_v2.sh [OPTIONS]
#
# Options:
#   --phase1-only       : Only collect URLs (Phase 1)
#   --phase2-only       : Only extract details (Phase 2)
#   --limit-urls N      : Limit URLs to collect per creator
#   --limit-details N   : Limit posts to extract details
#   --with-media        : Download media files after scraping
#   --with-tags         : Generate tags with AI after scraping
#   --with-notion       : Upload to Notion after processing
#   --summary           : Show Firebase tracking summary
#
# Examples:
#   ./daily_scrape_v2.sh                           # Run both phases
#   ./daily_scrape_v2.sh --phase1-only             # Only collect URLs
#   ./daily_scrape_v2.sh --phase2-only             # Only extract details
#   ./daily_scrape_v2.sh --limit-urls 10           # Limit URL collection
#   ./daily_scrape_v2.sh --summary                 # Show Firebase summary
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/home/javif/proyectos/astrologia/patreon"
cd "$PROJECT_DIR"

# Activate virtual environment
source venv/bin/activate

# Parse arguments
PHASE1_ONLY=false
PHASE2_ONLY=false
LIMIT_URLS=""
LIMIT_DETAILS=""
WITH_MEDIA=false
WITH_TAGS=false
WITH_NOTION=false
SUMMARY_ONLY=false

for arg in "$@"; do
    case $arg in
        --phase1-only)
            PHASE1_ONLY=true
            ;;
        --phase2-only)
            PHASE2_ONLY=true
            ;;
        --limit-urls)
            LIMIT_URLS="--limit-urls ${2}"
            shift
            ;;
        --limit-details)
            LIMIT_DETAILS="--limit-details ${2}"
            shift
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
        --summary)
            SUMMARY_ONLY=true
            ;;
    esac
    shift || true
done

# Log file
LOG_FILE="logs/daily_scrape_$(date +%Y%m%d_%H%M%S).log"

# Function to log and display
log_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

log_step() {
    echo -e "${CYAN}▶ $1${NC}"
    echo "▶ $1" >> "$LOG_FILE"
}

log_info() {
    echo -e "${YELLOW}  $1${NC}"
    echo "  $1" >> "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
    echo "✓ $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
    echo "✗ $1" >> "$LOG_FILE"
}

# Show header
log_header "Daily Patreon Scrape - Two-Phase Workflow"
echo -e "${YELLOW}Date: $(date)${NC}"
echo -e "${YELLOW}Log: $LOG_FILE${NC}"
echo ""

# If summary only
if [ "$SUMMARY_ONLY" = true ]; then
    log_step "Showing Firebase Summary"
    python src/firebase_tracker.py
    exit 0
fi

# Determine what to run
RUN_PHASE1=true
RUN_PHASE2=true

if [ "$PHASE1_ONLY" = true ]; then
    RUN_PHASE2=false
elif [ "$PHASE2_ONLY" = true ]; then
    RUN_PHASE1=false
fi

# ========== PHASE 1: COLLECT URLs ==========
if [ "$RUN_PHASE1" = true ]; then
    log_step "Phase 1: Collecting URLs from Patreon"
    log_info "Scanning all creators for new posts..."

    if python src/phase1_url_collector.py --all $LIMIT_URLS --headless 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Phase 1 complete"
    else
        log_error "Phase 1 failed"
        exit 1
    fi

    echo ""
fi

# ========== PHASE 2: EXTRACT DETAILS ==========
if [ "$RUN_PHASE2" = true ]; then
    log_step "Phase 2: Extracting Post Details"
    log_info "Processing posts pending detail extraction..."

    if python src/phase2_detail_extractor.py --all $LIMIT_DETAILS --headless 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Phase 2 complete"
    else
        log_error "Phase 2 failed"
        exit 1
    fi

    echo ""
fi

# ========== OPTIONAL: DOWNLOAD MEDIA ==========
if [ "$WITH_MEDIA" = true ]; then
    log_step "Downloading Media Files"

    if python src/media_downloader.py --all 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Media download complete"
    else
        log_error "Media download failed"
    fi

    echo ""
fi

# ========== OPTIONAL: GENERATE TAGS ==========
if [ "$WITH_TAGS" = true ]; then
    log_step "Generating AI Tags"

    if [ -z "$GEMINI_API_KEY" ]; then
        log_error "GEMINI_API_KEY not set. Skipping tag generation."
    else
        if python src/tag_generator.py --all 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Tag generation complete"
        else
            log_error "Tag generation failed"
        fi
    fi

    echo ""
fi

# ========== OPTIONAL: UPLOAD TO NOTION ==========
if [ "$WITH_NOTION" = true ]; then
    log_step "Uploading to Notion"

    if [ -z "$NOTION_API_KEY" ]; then
        log_error "NOTION_API_KEY not set. Skipping Notion upload."
    else
        if python src/notion_integrator.py --all 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Notion upload complete"
        else
            log_error "Notion upload failed"
        fi
    fi

    echo ""
fi

# ========== FINAL SUMMARY ==========
log_header "Workflow Complete"
log_step "Showing Firebase Summary"
python src/firebase_tracker.py

echo ""
echo -e "${GREEN}✅ Daily scrape complete!${NC}"
echo -e "${BLUE}   Log file: $LOG_FILE${NC}"
echo ""

exit 0
