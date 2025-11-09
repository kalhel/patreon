# 📚 Legacy V1 Columns - Migration Documentation

**Date:** 2025-11-09
**Branch:** `feature/advanced-search-improvements`
**Status:** ✅ Documented, not removed yet

---

## 🎯 Purpose

This migration documents legacy V1 columns in the `posts` table as **DEPRECATED**. These columns are kept for backward compatibility but should not be used in new code.

---

## 📊 Legacy V1 vs V2 Schema

### V1 (Legacy - Pre Multi-Source)
```sql
posts.creator_id      VARCHAR   -- "headonhistory", "astrobymax"
posts.creator_name    VARCHAR   -- "Ali A Olomi", "AstroByMax"
posts.creator_avatar  TEXT      -- Avatar URL/path
posts.patreon_tags    TEXT[]    -- Platform-specific naming
```

### V2 (Current - Multi-Source)
```sql
posts.source_id       INTEGER   -- FK to creator_sources (multi-platform)

-- Access creator info via JOIN:
posts → creator_sources → creators
  ↓            ↓               ↓
source_id      platform      name, avatar_filename
```

---

## 🚀 Applied Migrations

### 1. Document Legacy Columns (2025-11-09)

**File:** `2025-11-09_document_legacy_v1_columns.sql`

**What it does:**
- Adds `COMMENT` to `creator_id`, `creator_name`, `creator_avatar` marking them as DEPRECATED
- Adds `COMMENT` to `patreon_tags` suggesting rename to `tags`
- Adds `COMMENT` to `source_id` marking it as V2 standard

**How to apply:**
```bash
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 \
  -f database/migrations/2025-11-09_document_legacy_v1_columns.sql
```

**Output:**
```
✅ Legacy V1 columns documented as DEPRECATED
✅ source_id documented as V2 standard

📊 Current state:
 total_posts | has_source_id_v2 | has_creator_id_v1 | has_creator_name_v1
-------------+------------------+-------------------+---------------------
         982 |              982 |               982 |                 905
```

---

## 🔄 Rollback Instructions

### Rollback Migration (Remove Documentation)

**File:** `2025-11-09_rollback_legacy_documentation.sql`

**What it does:**
- Removes all `COMMENT` documentation from columns
- Does NOT remove the columns themselves

**How to rollback:**
```bash
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 \
  -f database/migrations/2025-11-09_rollback_legacy_documentation.sql
```

**Output:**
```
✅ All column comments removed (rollback complete)
```

---

## 📝 Viewing Column Comments

### Check which columns are documented:
```sql
SELECT
    column_name,
    col_description('posts'::regclass, ordinal_position) as description
FROM information_schema.columns
WHERE table_name = 'posts'
  AND column_name IN ('creator_id', 'creator_name', 'creator_avatar', 'patreon_tags', 'source_id')
ORDER BY column_name;
```

### Expected output after migration:
```
column_name   | description
--------------+-----------------------------------------------------
creator_id    | DEPRECATED (V1): Legacy string identifier...
creator_name  | DEPRECATED (V1): Denormalized creator name...
creator_avatar| DEPRECATED (V1): Legacy avatar URL/path...
patreon_tags  | PLATFORM-SPECIFIC: Should be renamed to "tags"...
source_id     | V2 STANDARD: Foreign key to creator_sources...
```

---

## 🗺️ Migration Roadmap

### Phase 1: Documentation (✅ DONE - 2025-11-09)
- [x] Add COMMENT to legacy columns
- [x] Create rollback script
- [x] Document migration process

### Phase 2: Code Migration (⏳ FUTURE)
- [ ] Update `viewer.py` to use `source_id` JOINs instead of `creator_id`
- [ ] Update scrapers to stop populating `creator_name`, `creator_avatar`
- [ ] Create SQL views for backward compatibility

### Phase 3: Column Rename (⏳ FUTURE)
- [ ] Rename `patreon_tags` → `tags`
- [ ] Update all code references
- [ ] Update indexes

### Phase 4: Column Removal (⏳ FAR FUTURE)
- [ ] Remove `creator_id` column (after all code migrated)
- [ ] Remove `creator_name` column (after all code migrated)
- [ ] Remove `creator_avatar` column (after all code migrated)

---

## ⚠️ Important Notes

### Why Keep Legacy Columns?

1. **Backward Compatibility:** Existing code relies on these columns
2. **Gradual Migration:** Allows incremental refactoring without breaking changes
3. **Safety:** Can rollback if issues arise

### When to Remove Legacy Columns?

**DO NOT REMOVE** until:
- ✅ All code uses `source_id` JOINs instead of `creator_id`
- ✅ Scrapers don't populate `creator_name`, `creator_avatar`
- ✅ Frontend doesn't reference these fields
- ✅ Exports/backups don't depend on them

---

## 📚 Related Documentation

- `docs/DATABASE_DESIGN_REVIEW.md` - Multi-source schema analysis
- `docs/MIGRATION_LEGACY_V1_COLUMNS.md` - Detailed migration plan
- `docs/SEARCH_IMPROVEMENTS_PLAN.md` - Search system migration

---

## 🧪 Testing

### Verify migration applied correctly:
```bash
# Should show comments on all 5 columns
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 -c "
SELECT column_name, substring(col_description('posts'::regclass, ordinal_position), 1, 50) as comment_preview
FROM information_schema.columns
WHERE table_name = 'posts' AND column_name IN ('creator_id', 'creator_name', 'creator_avatar', 'patreon_tags', 'source_id');
"
```

### Verify rollback works:
```bash
# Apply rollback
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 \
  -f database/migrations/2025-11-09_rollback_legacy_documentation.sql

# Comments should all be NULL
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 -c "
SELECT column_name, col_description('posts'::regclass, ordinal_position) as comment
FROM information_schema.columns
WHERE table_name = 'posts' AND column_name IN ('creator_id', 'source_id');
"

# Re-apply if needed
PGPASSWORD='your_password' psql -U patreon_user -d alejandria -h 127.0.0.1 \
  -f database/migrations/2025-11-09_document_legacy_v1_columns.sql
```

---

## 🔐 Security Note

**IMPORTANT:** These migration scripts use PostgreSQL `COMMENT` which is DDL (Data Definition Language).

- ✅ **Safe:** Does NOT modify data
- ✅ **Safe:** Does NOT modify schema structure
- ✅ **Safe:** Only adds metadata for developers
- ✅ **Reversible:** Can be rolled back with rollback script

---

**Last Updated:** 2025-11-09
**Maintained By:** Javi + Claude
**Status:** Active - Phase 1 Complete
