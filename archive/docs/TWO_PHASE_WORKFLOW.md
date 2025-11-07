# Two-Phase Workflow with Firebase Tracking

## Overview

This project uses a **two-phase workflow** with Firebase Realtime Database for tracking processing state.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FIREBASE REALTIME DB                      │
│  Tracks: URLs collected, Details extracted, Notion uploaded  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
              ┌───────────────┴───────────────┐
              │                               │
      ┌───────▼───────┐              ┌───────▼────────┐
      │   PHASE 1     │              │   PHASE 2      │
      │ URL Collector │──────────────▶│Detail Extractor│
      └───────────────┘              └────────────────┘
              │                               │
              │                               │
      ┌───────▼────────┐              ┌──────▼─────────┐
      │ Patreon Feed   │              │ Individual     │
      │ (Load More)    │              │ Post Pages     │
      └────────────────┘              └────────────────┘
```

---

## Phase 1: URL Collection

**Purpose**: Quickly scan all creators and collect post URLs

**Script**: `src/phase1_url_collector.py`

**What it does**:
- Navigates to each creator's feed
- Clicks "Load more" to load all posts
- Extracts post URLs and IDs
- Creates records in Firebase with `url_collected: true`
- Fast: Only extracts URLs, no content

**Usage**:
```bash
# Collect URLs from all creators
python src/phase1_url_collector.py --all

# Collect URLs from single creator
python src/phase1_url_collector.py --creator headonhistory

# Limit URLs per creator
python src/phase1_url_collector.py --all --limit 10
```

---

## Phase 2: Detail Extraction

**Purpose**: Extract full content from posts tracked in Firebase

**Script**: `src/phase2_detail_extractor.py`

**What it does**:
- Queries Firebase for posts with `url_collected: true` and `details_extracted: false`
- Visits each post's individual page
- Extracts: title, full content, images, videos, audio, comments, tags
- Marks in Firebase as `details_extracted: true`
- Saves detailed JSON to `data/processed/`

**Usage**:
```bash
# Extract details for all pending posts
python src/phase2_detail_extractor.py --all

# Extract details for single creator
python src/phase2_detail_extractor.py --creator headonhistory

# Extract details for specific post
python src/phase2_detail_extractor.py --post 142518617

# Limit number of posts to process
python src/phase2_detail_extractor.py --all --limit 5
```

---

## Orchestrator

**Purpose**: Run both phases automatically

**Script**: `src/orchestrator.py`

**What it does**:
- Runs Phase 1 to collect new URLs
- Immediately runs Phase 2 to extract details
- Updates Firebase throughout
- Shows final summary

**Usage**:
```bash
# Run complete workflow for all creators
python src/orchestrator.py --all

# Run workflow for single creator
python src/orchestrator.py --creator headonhistory

# Run with limits
python src/orchestrator.py --all --limit-urls 5 --limit-details 10
```

---

## Firebase Structure

### Posts Collection

```json
{
  "posts": {
    "142518617": {
      "post_id": "142518617",
      "creator_id": "headonhistory",
      "post_url": "https://www.patreon.com/posts/...",
      "status": {
        "url_collected": true,
        "url_collected_at": "2025-11-01T12:00:00",
        "details_extracted": true,
        "details_extracted_at": "2025-11-01T12:05:00",
        "uploaded_to_notion": false,
        "uploaded_to_notion_at": null,
        "last_attempt": "2025-11-01T12:05:00",
        "attempt_count": 1,
        "errors": []
      },
      "notion_page_id": null,
      "created_at": "2025-11-01T12:00:00",
      "updated_at": "2025-11-01T12:05:00"
    }
  }
}
```

### Creators Stats

```json
{
  "creators": {
    "headonhistory": {
      "creator_id": "headonhistory",
      "last_scrape": "2025-11-01T12:00:00",
      "total_posts": 150,
      "processed_posts": 145,
      "pending_posts": 5,
      "updated_at": "2025-11-01T12:00:00"
    }
  }
}
```

---

## Daily Automation

### Script: `daily_scrape_v2.sh`

**Cron setup** (runs daily at 3 AM):
```bash
crontab -e

# Add this line:
0 3 * * * /home/javif/proyectos/astrologia/patreon/daily_scrape_v2.sh
```

**Manual execution**:
```bash
# Run both phases
./daily_scrape_v2.sh

# Only collect URLs (Phase 1)
./daily_scrape_v2.sh --phase1-only

# Only extract details (Phase 2)
./daily_scrape_v2.sh --phase2-only

# Show Firebase summary
./daily_scrape_v2.sh --summary

# Run with media download and tag generation
./daily_scrape_v2.sh --with-media --with-tags
```

---

## Advantages of Two-Phase Design

### 1. **Speed**
- Phase 1 is fast: Only collects URLs
- Can run Phase 1 frequently to catch new posts immediately

### 2. **Reliability**
- If Phase 2 fails, URLs are already saved in Firebase
- Can retry detail extraction without re-scanning feeds

### 3. **Resource Management**
- Phase 1: Low resource usage (quick page scans)
- Phase 2: High resource usage (detailed extraction)
- Can run them at different times

### 4. **Incremental Processing**
- Daily automation only processes new posts
- Firebase tracks what's been processed
- No duplicate work

### 5. **Debugging**
- Easy to see which phase failed
- Can re-run specific phase without affecting the other
- Firebase provides audit trail

### 6. **Scalability**
- Can run multiple Phase 2 workers in parallel
- Firebase handles concurrency
- Phase 1 can run independently

---

## Monitoring

### Check Firebase Status

```bash
# Show summary
python src/firebase_tracker.py

# Or use orchestrator
python src/orchestrator.py --summary
```

**Output**:
```
============================================================
🔥 FIREBASE TRACKING SUMMARY
============================================================
Total Posts:        150
URLs Collected:     150
Details Extracted:  145
Uploaded to Notion: 140

Pending Details:    5
Pending Upload:     5

============================================================
CREATORS:
============================================================

headonhistory:
  Total:     50
  Processed: 48
  Pending:   2

astrobymax:
  Total:     60
  Processed: 58
  Pending:   2

horoiproject:
  Total:     40
  Processed: 39
  Pending:   1
============================================================
```

---

## Typical Workflows

### Initial Setup (First Run)

```bash
# 1. Collect all URLs from all creators
python src/phase1_url_collector.py --all

# 2. Extract details for all posts
python src/phase2_detail_extractor.py --all

# 3. Check summary
python src/orchestrator.py --summary
```

### Daily Automation

```bash
# Automated via cron at 3 AM daily
0 3 * * * /home/javif/proyectos/astrologia/patreon/daily_scrape_v2.sh
```

### Manual Check for New Posts

```bash
# Quick check: Only collect new URLs
python src/phase1_url_collector.py --all

# Then extract details for new posts
python src/phase2_detail_extractor.py --all
```

### Process Single Creator

```bash
# Complete workflow for one creator
python src/orchestrator.py --creator headonhistory
```

### Retry Failed Posts

```bash
# Firebase tracks failed attempts
# Just re-run Phase 2, it will process pending posts
python src/phase2_detail_extractor.py --all
```

---

## Error Handling

### Automatic Retry
- Firebase tracks `attempt_count` and `errors`
- Failed posts remain with `details_extracted: false`
- Next run will retry them

### Manual Intervention

**Check specific post**:
```bash
# View post in Firebase
python -c "from firebase_tracker import *; t = FirebaseTracker(*load_firebase_config()); print(t.get_post('142518617'))"
```

**Force re-extract specific post**:
```bash
python src/phase2_detail_extractor.py --post 142518617
```

---

## File Output

### Phase 1 Output
- Firebase records only
- No local JSON files (except raw data in `data/raw/`)

### Phase 2 Output
- `data/processed/{creator_id}_posts_detailed.json`
- Complete post data with all media URLs

**Example**:
```json
{
  "post_id": "142518617",
  "creator_id": "headonhistory",
  "post_url": "https://...",
  "title": "Demon Queen of History",
  "full_content": "Lorem ipsum...",
  "images": ["https://..."],
  "videos": ["https://..."],
  "audios": ["https://..."],
  "patreon_tags": ["history", "medieval"],
  "status": { ... }
}
```

---

## Next Steps

After Phase 2 completes:
1. **Download Media**: `python src/media_downloader.py --all`
2. **Generate Tags**: `python src/tag_generator.py --all`
3. **Upload to Notion**: `python src/notion_integrator.py --all`

Or run all at once:
```bash
./daily_scrape_v2.sh --with-media --with-tags --with-notion
```

---

## Configuration

Firebase configuration is in `config/credentials.json`:

```json
{
  "firebase": {
    "database_url": "https://patreon-57f6c-default-rtdb.europe-west1.firebasedatabase.app/",
    "database_secret": "YOUR_SECRET_HERE"
  }
}
```

---

## Logs

All operations are logged:
- `logs/phase1_url_collector.log`
- `logs/phase2_detail_extractor.log`
- `logs/orchestrator.log`
- `logs/daily_scrape_YYYYMMDD_HHMMSS.log`

---

## Summary

The two-phase workflow provides:
- ✅ Fast URL discovery
- ✅ Reliable state tracking with Firebase
- ✅ Incremental processing (no duplicate work)
- ✅ Easy monitoring and debugging
- ✅ Automatic daily updates
- ✅ Scalable architecture

Each phase can run independently, making the system resilient and flexible.
