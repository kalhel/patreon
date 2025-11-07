# PostgreSQL Migration Plan

**Date:** 2025-11-07
**Branch:** `migration/postgresql-full-integration`
**Rollback Tag:** `pre-postgresql-migration`

## Overview

This document outlines the complete migration from JSON-based storage to PostgreSQL database for the Patreon scraper project.

## Current Status

- ✅ PostgreSQL schema created (`database/schema_posts.sql`)
- ✅ Posts migrated to PostgreSQL (982 posts)
- ❌ Collections NOT migrated yet (still in JSON)
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

## FASE 1: Collections Migration 📦

### Goal:
Migrate all collections from JSON files to PostgreSQL tables.

### Input:
- `data/processed/*_collections.json`

### Output:
- PostgreSQL tables: `collections`, `post_collections`

### Script:
- `src/migrate_collections_to_postgres.py` (to be created)

### Features:
- Pre-flight checks (similar to posts migration)
- Validation of JSON structure
- Skip duplicates (collection_id)
- Detailed progress logging
- Statistics report

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

### 2.1 Phase 1 URL Collector (`src/phase1_url_collector.py`)

**Current behavior:**
- Collects post URLs from creator pages
- Saves to: `data/raw/{creator}_posts.json`

**New behavior:**
- Collect post URLs
- Insert into PostgreSQL `posts` table (basic info only)
- **DUAL MODE:** Also save to JSON as backup (temporary)

**Changes needed:**
- Import `PostgresTracker` or create `PostgresPostsWriter`
- Add `save_to_postgres()` method
- Add flag check: `config/use_postgresql.flag`

**Rollback:**
- Git revert the commit
- JSON files remain untouched

---

### 2.2 Phase 2 Detail Extractor (`src/phase2_detail_extractor.py`)

**Current behavior:**
- Reads from: `data/raw/{creator}_posts.json`
- Extracts full post details (content, media, etc.)
- Saves to: `data/processed/{creator}_posts_detailed.json`

**New behavior:**
- Read from PostgreSQL `posts` table (filter by `status.details_extracted = false`)
- Extract full post details
- Update PostgreSQL `posts` table with full data
- **DUAL MODE:** Also save to JSON as backup (temporary)

**Changes needed:**
- Import database connection
- Read posts from PostgreSQL
- Update posts in PostgreSQL with new content_blocks, media paths
- Add flag check: `config/use_postgresql.flag`

**Rollback:**
- Git revert the commit
- JSON files remain untouched

---

### 2.3 Phase 3 Collections Scraper (`src/phase3_collections_scraper.py`)

**Current behavior:**
- Scrapes collections from creator pages
- Saves to: `data/processed/{creator}_collections.json`
- Updates posts with collection info in JSON

**New behavior:**
- Scrape collections
- Insert into PostgreSQL `collections` table
- Create relationships in `post_collections` table
- Update post collection references
- **DUAL MODE:** Also save to JSON as backup (temporary)

**Changes needed:**
- Import database connection
- Insert collections into PostgreSQL
- Create many-to-many relationships
- Add flag check: `config/use_postgresql.flag`

**Rollback:**
- Git revert the commit
- JSON files remain untouched

---

## FASE 3: Web Viewer Update 🌐

### Goal:
Update web viewer to read from PostgreSQL with fallback to JSON.

### Files to modify:
- `web/viewer.py`
- `web/templates/settings.html`

### Strategy: Dual Mode with Flag

```python
# web/viewer.py
import os
from pathlib import Path

USE_POSTGRES = os.path.exists('config/use_postgresql.flag')

def load_all_posts():
    """Load posts from PostgreSQL or JSON based on flag"""
    if USE_POSTGRES:
        return load_posts_from_postgres()
    else:
        return load_posts_from_json()  # Existing code

def load_posts_from_postgres():
    """Load posts from PostgreSQL database"""
    from sqlalchemy import create_engine, text
    # ... implementation

def load_posts_from_json():
    """Load posts from JSON files (existing code)"""
    # Keep existing implementation unchanged
```

### Changes needed:

**1. Create database helper:**
- `web/db_helper.py` - Database connection and query functions

**2. Update `load_all_posts()` function:**
- Check flag
- Branch to PostgreSQL or JSON loader

**3. Update `settings.html`:**
- Show PostgreSQL stats if enabled
- Show JSON file stats if disabled

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
2. 📦 **FASE 1:** Migrate collections to PostgreSQL
3. 🔄 **FASE 2.3:** Update Phase 3 collections scraper
4. 🔄 **FASE 2.2:** Update Phase 2 detail extractor
5. 🔄 **FASE 2.1:** Update Phase 1 URL collector
6. 🌐 **FASE 3:** Update web viewer with dual mode
7. ✅ **FASE 4:** Complete testing and validation

---

## Safety Principles

1. **Never delete JSON files** until PostgreSQL is proven 100% stable
2. **Dual mode for 1+ week** - Scripts save to both PostgreSQL AND JSON
3. **Flag-based activation** - Instant rollback without code changes
4. **Git tags** - Quick revert to previous state
5. **Comprehensive backups** - All critical files backed up before changes

---

## Current Progress

- ✅ FASE 0.1: Migration branch created
- ✅ FASE 0.2: Backups created
- ✅ FASE 0.3: Git tag created
- ✅ FASE 0.4: Documentation created
- ⏳ FASE 1: Collections migration (next step)

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
