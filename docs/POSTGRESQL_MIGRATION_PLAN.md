# PostgreSQL Migration Plan

**Date:** 2025-11-07
**Branch:** `migration/postgresql-full-integration`
**Rollback Tag:** `pre-postgresql-migration`

## Overview

This document outlines the complete migration from JSON-based storage to PostgreSQL database for the Patreon scraper project.

## Current Status

- ✅ PostgreSQL schema created (`database/schema_posts.sql`)
- ✅ Posts migrated to PostgreSQL (982 posts)
- ✅ Collections migrated to PostgreSQL (30 collections, 259 post-collection relationships)
- ❌ Web viewer still reads from JSON
- ❌ Scraping scripts (Phase 1, 2, 3) still write to JSON

## Migration Goals

1. **Migrate collections** from JSON to PostgreSQL (tables: `collections`, `post_collections`)
2. **Update scraping scripts** to write directly to PostgreSQL
3. **Update web viewer** to read from PostgreSQL with fallback to JSON
4. **Maintain rollback capability** at every step

---

## FASE 0: Preparation and Backup ✅

### What was done:
```bash
# 1. Created migration branch
git checkout -b migration/postgresql-full-integration

# 2. Created backups
mkdir -p backups/pre-migration
cp web/viewer.py backups/pre-migration/
cp src/phase1_url_collector.py backups/pre-migration/
cp src/phase2_detail_extractor.py backups/pre-migration/
cp src/phase3_collections_scraper.py backups/pre-migration/

# 3. Created rollback tag
git tag -a pre-postgresql-migration -m "Tag before PostgreSQL full migration"
```

### Rollback Strategy:
```bash
# Option 1: Delete PostgreSQL flag (instant rollback)
rm config/use_postgresql.flag

# Option 2: Revert specific commits
git revert <commit-hash>

# Option 3: Hard reset to tag
git reset --hard pre-postgresql-migration
```

---

## FASE 1: Collections Migration ✅

### Goal:
Migrate all collections from JSON files to PostgreSQL tables.

### Input:
- `data/processed/*_collections.json`

### Output:
- PostgreSQL tables: `collections`, `post_collections`

### Script:
- `src/migrate_collections_to_postgres.py` ✅
- `fix_collections_schema.py` (helper script for schema fixes)

### Results:
- ✅ **30 collections migrated** successfully
- ✅ **259 post-collection relationships** created
- ✅ **0 errors** during migration
- Distribution:
  - horoiproject: 20 collections
  - astrobymax: 8 collections
  - headonhistory: 1 collection
  - skyscript: 1 collection

### Features Implemented:
- ✅ Pre-flight checks (database connection, schema, JSON structure, permissions)
- ✅ Validation of JSON structure
- ✅ Skip duplicates (collection_id)
- ✅ Detailed progress logging
- ✅ Statistics report with per-creator breakdown
- ✅ Foreign key validation before insertion

### Rollback:
```sql
-- Clear collections data (keeps schema)
TRUNCATE collections, post_collections CASCADE;

-- Or drop and recreate tables
DROP TABLE IF EXISTS post_collections CASCADE;
DROP TABLE IF EXISTS collections CASCADE;

-- Then re-apply schema
psql $DATABASE_URL -f database/schema_posts.sql
```

---

## FASE 2: Update Scraping Scripts 🔄

### 2.1 Phase 1 URL Collector ✅ (`src/phase1_url_collector.py`)

**Current behavior:**
- Collects post URLs from creator pages
- **Already uses PostgresTracker** to save directly to PostgreSQL
- Never saved to JSON (previously used Firebase)

**Status: NO CHANGES NEEDED**
- ✅ Already imports and uses `PostgresTracker`
- ✅ Already calls `tracker.create_post_record()` for each post
- ✅ Already checks `tracker.post_exists()` to avoid duplicates
- ✅ Already calls `tracker.update_creator_stats()`
- ✅ PostgreSQL integration complete since initial implementation

**Note:**
Phase 1 was already migrated from Firebase to PostgreSQL before this migration plan.
It never used JSON storage, so no dual mode is needed.

---

### 2.2 Phase 2 Detail Extractor ✅ (`src/phase2_detail_extractor.py`)

**Current behavior:**
- Already reads from PostgreSQL via `PostgresTracker`
- Extracts full post details (content, media, etc.)
- Saves to: `data/processed/{creator}_posts_detailed.json`
- Only marks `details_extracted = true` in database

**New behavior (IMPLEMENTED):**
- Read from PostgreSQL `posts` table (via PostgresTracker)
- Extract full post details
- Update PostgreSQL `posts` table with full data (content_blocks, media paths, etc.)
- **DUAL MODE:** Always saves to JSON + PostgreSQL if flag enabled

**Changes completed:**
- ✅ Import database connection (sqlalchemy, dotenv, quote_plus)
- ✅ Added `use_postgresql()` function to check flag
- ✅ Added `get_database_url()` function to build connection from .env
- ✅ Created `update_post_details_in_postgres()` function
- ✅ Updates posts with: title, content, content_blocks, video_streams, video_subtitles, media paths, tags
- ✅ Modified `extract_post_details()` to use dual mode
- ✅ Graceful error handling for PostgreSQL failures

**Rollback:**
- Git revert the commit
- JSON files remain untouched
- Or simply remove `config/use_postgresql.flag`

---

### 2.3 Phase 3 Collections Scraper ✅ (`src/phase3_collections_scraper.py`)

**Current behavior:**
- Scrapes collections from creator pages
- Saves to: `data/processed/{creator}_collections.json`
- Updates posts with collection info in JSON

**New behavior (IMPLEMENTED):**
- Scrape collections
- Insert into PostgreSQL `collections` table
- Create relationships in `post_collections` table
- **DUAL MODE:** Always saves to JSON + PostgreSQL if flag enabled

**Changes completed:**
- ✅ Import database connection (sqlalchemy, dotenv)
- ✅ Added `use_postgresql()` function to check flag
- ✅ Added `save_collections_to_postgres()` function
- ✅ Inserts collections with ON CONFLICT to handle duplicates
- ✅ Creates many-to-many relationships in `post_collections` table
- ✅ Maintains `order_in_collection` for proper sorting
- ✅ Modified `save_collections_data()` to use dual mode

**Rollback:**
- Git revert commit `1f4a2b1`
- JSON files remain untouched
- Or simply remove `config/use_postgresql.flag`

---

## FASE 3: Web Viewer Update ✅

### Goal:
Update web viewer to read from PostgreSQL with fallback to JSON.

### Files modified:
- ✅ `web/viewer.py` - Main viewer with dual mode support
- `web/templates/settings.html` (optional - future enhancement)

### Changes completed:

**1. Updated `web/viewer.py`:**
- ✅ Added PostgreSQL imports (dotenv, sqlalchemy, quote_plus)
- ✅ Created `use_postgresql()` - Checks for flag file
- ✅ Created `get_database_url()` - Builds connection from .env
- ✅ Created `load_posts_from_postgres()` - Loads all posts from PostgreSQL
- ✅ Created `load_posts_from_json()` - Original JSON loading logic (extracted)
- ✅ Modified `load_all_posts()` - Dual mode with automatic fallback

**2. Dual mode behavior:**
- If flag exists: Loads from PostgreSQL
- If PostgreSQL fails: Automatic fallback to JSON
- If flag doesn't exist: Loads from JSON directly
- Graceful error handling with user-friendly messages

**3. PostgreSQL query:**
- Loads all non-deleted posts
- Retrieves all 24 columns including content_blocks, media paths, tags
- Converts timestamps to ISO format for JSON compatibility
- Orders by post_id DESC (newest first)

**4. Test script created:**
- `test_web_viewer_postgres.py` - 4 comprehensive tests
- Tests flag detection, database connection, post loading, function imports

### Activation:
```bash
# Enable PostgreSQL mode
touch config/use_postgresql.flag

# Disable PostgreSQL mode (instant rollback)
rm config/use_postgresql.flag
```

### Rollback:
```bash
# Instant rollback (no code changes needed)
rm config/use_postgresql.flag

# Or git revert
git revert <commit-hash>
```

---

## FASE 4: Testing and Validation ✅

### Test Checklist:

**Database Tests:**
- [ ] Count posts: PostgreSQL vs JSON match
- [ ] Count collections: PostgreSQL vs JSON match
- [ ] Verify foreign key relationships work
- [ ] Test full-text search queries
- [ ] Test collection queries

**Web Viewer Tests:**
- [ ] Homepage loads correctly
- [ ] Individual posts display correctly
- [ ] Collections page works
- [ ] Search functionality works
- [ ] Settings page shows correct stats
- [ ] Media files load correctly (images, videos, audio)

**Scraping Tests:**
- [ ] Phase 1: URL collection saves to PostgreSQL
- [ ] Phase 2: Detail extraction updates PostgreSQL
- [ ] Phase 3: Collections saved to PostgreSQL
- [ ] Verify no duplicates created
- [ ] Verify JSON backups still created

**Performance Tests:**
- [ ] Homepage load time (PostgreSQL vs JSON)
- [ ] Search response time
- [ ] Individual post load time

**Flag Toggle Tests:**
- [ ] Create flag → web viewer uses PostgreSQL
- [ ] Remove flag → web viewer uses JSON
- [ ] Toggle multiple times → no errors

---

## Execution Order

1. ✅ **FASE 0:** Backups + branch + tag + documentation
2. ✅ **FASE 1:** Migrate posts and collections to PostgreSQL
3. ✅ **FASE 2.3:** Update Phase 3 collections scraper
4. ✅ **FASE 2.2:** Update Phase 2 detail extractor
5. ✅ **FASE 2.1:** Phase 1 URL collector (already uses PostgreSQL)
6. ✅ **FASE 3:** Update web viewer with dual mode
7. ⏳ **FASE 4:** Complete testing and validation (next)

---

## Safety Principles

1. **Never delete JSON files** until PostgreSQL is proven 100% stable
2. **Dual mode for 1+ week** - Scripts save to both PostgreSQL AND JSON
3. **Flag-based activation** - Instant rollback without code changes
4. **Git tags** - Quick revert to previous state
5. **Comprehensive backups** - All critical files backed up before changes

---

## Current Progress

- ✅ FASE 0: Migration preparation completed
  - ✅ Migration branch created
  - ✅ Backups created
  - ✅ Git tag created
  - ✅ Documentation created
- ✅ FASE 1: Data migration completed
  - ✅ Posts migrated (982 posts)
  - ✅ Collections migrated (30 collections, 259 relationships)
- ✅ FASE 2: Update scraping scripts (completed)
  - ✅ Phase 3 collections scraper (dual mode implemented)
  - ✅ Phase 2 detail extractor (dual mode implemented)
  - ✅ Phase 1 URL collector (already uses PostgreSQL)
- ✅ FASE 3: Web viewer update (completed)
  - ✅ Dual mode with PostgreSQL support
  - ✅ Automatic fallback to JSON
  - ✅ Test script created

---

## Rollback Points

| Phase | Rollback Method | Data Loss Risk |
|-------|----------------|----------------|
| FASE 0 | `git reset --hard pre-postgresql-migration` | None (nothing changed yet) |
| FASE 1 | `TRUNCATE collections, post_collections` | Collections only (can re-migrate from JSON) |
| FASE 2 | `git revert <commit>` | None (JSON files untouched) |
| FASE 3 | `rm config/use_postgresql.flag` | None (instant fallback to JSON) |

---

## Success Criteria

Migration is considered successful when:

1. ✅ All collections migrated to PostgreSQL without data loss
2. ✅ All scraping scripts write to PostgreSQL successfully
3. ✅ Web viewer displays all data correctly from PostgreSQL
4. ✅ Full-text search works correctly
5. ✅ No performance degradation
6. ✅ Flag toggle works correctly (PostgreSQL ↔ JSON)
7. ✅ All tests pass

---

## Next Steps

After successful migration:

1. Monitor PostgreSQL performance for 1 week
2. Keep dual mode (PostgreSQL + JSON) for 1 week
3. Gradually disable JSON writing if PostgreSQL stable
4. Archive old JSON files (don't delete)
5. Update documentation
6. Merge to main branch

---

## Contact & Support

**Documentation:** This file
**Branch:** `migration/postgresql-full-integration`
**Rollback Tag:** `pre-postgresql-migration`
**Backups:** `backups/pre-migration/`
