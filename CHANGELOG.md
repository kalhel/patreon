# Changelog

All notable changes to this project will be documented in this file.

## [2025-11-06] - Major Updates

### Added
- **Daily Incremental Scraper** (`src/daily_incremental_scrape.py`)
  - Optimized scraper for daily updates
  - Only collects NEW posts (stops at first known post)
  - 10-100x faster than full scrape
  - Perfect for cron jobs

- **Creator Management Tools** (in `src/`)
  - `add_creator.py` - Add creators from command line
  - `reset_creator.py` - Reset individual creator data with backup

- **Diagnostic Tools** (in `src/`)
  - `diagnose_headonhistory.py` - Debug missing creator issues
  - `debug_creators.py` - Check creator post distribution
  - `fix_corrupted_json.py` - Repair corrupted JSON files

- **Collections View** (Web UI)
  - Toggle to show collections instead of posts
  - Aggregated stats per collection
  - Square thumbnail images (150x150px)
  - Filters by creator

### Fixed
- **Critical: Settings save deleting credentials.json**
  - Added triple validation layer
  - Automatic backup before save
  - Comparison check prevents data loss

- **Video thumbnails showing black screen**
  - Added `#t=0.1` to video sources
  - Shows first frame as thumbnail

- **phase1_url_collector not finding creators**
  - Now loads creators from `creators.json` correctly
  - Fixed config loading logic

- **Settings UI showing wrong Firebase fields**
  - Updated to use `database_secret` instead of `credentials_path`
  - Password field for secret protection

### Changed
- **Project Structure**
  - Moved utility scripts to `tools/` directory
  - Moved main scripts to `src/` directory
  - Better organization and clarity

- **Firebase Configuration**
  - Now uses `database_secret` for authentication
  - Removed deprecated `credentials_path` field

## Workflow Changes

### Daily Updates (NEW - Recommended)
```bash
# 1. Incremental scrape (only new posts)
python src/daily_incremental_scrape.py --all

# 2. Process pending details
python src/phase2_detail_extractor.py --all --headless

# 3. Update collections
python src/phase3_collections_scraper.py --all --headless
```

### Initial/Full Scrape (When adding new creator)
```bash
# 1. Full URL collection
python src/phase1_url_collector.py --creator CREATOR_NAME

# 2. Extract all details
python src/phase2_detail_extractor.py --creator CREATOR_NAME --headless

# 3. Scrape collections
python src/phase3_collections_scraper.py --creator CREATOR_NAME --headless
```

## Breaking Changes

### credentials.json Format
**Old:**
```json
{
  "firebase": {
    "credentials_path": "path/to/file.json",
    "database_url": "..."
  }
}
```

**New:**
```json
{
  "firebase": {
    "database_url": "...",
    "database_secret": "YOUR_SECRET_HERE"
  }
}
```

## Known Issues

None at this time.

## Migration Guide

If upgrading from earlier version:

1. **Update credentials.json:**
   - Remove `credentials_path` field
   - Add `database_secret` field (get from Firebase Console)

2. **Update any scripts/cron jobs:**
   - Change `daily_scrape_v2.sh` to use `daily_incremental_scrape.py` for faster updates

3. **Pull latest code:**
   ```bash
   git pull
   ```

## Contributors

- Claude (AI Assistant)
- Project Owner
