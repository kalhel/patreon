# Phase 2 PostgreSQL Integration - Testing Guide

## 🐛 Schema Fix Applied

Fixed column mismatch issues:
- ✅ Changed `content` → `full_content`
- ✅ Removed `edited_at` (doesn't exist in schema)
- ✅ Removed `video_subtitles_relative` (not a separate column)
- ✅ Added logic to extract `full_content` from `content_blocks`

## 🧪 Test Script

**File:** `test_phase2_postgres.py`

**Tests:**
1. Flag Detection - Verifies `config/use_postgresql.flag` exists
2. Database Connection - Tests PostgreSQL connection
3. Posts Table - Checks posts table exists and has data
4. Update Post Details - Tests updating a post with sample data

## ▶️ How to Run

```bash
# Activate your Python environment first
# Then run:
python test_phase2_postgres.py
```

## ✅ Expected Output

```
============================================================
🧪 Phase 2 PostgreSQL Integration Tests
============================================================

============================================================
TEST 1: Flag Detection
============================================================
✅ PostgreSQL flag detected

============================================================
TEST 2: Database Connection
============================================================
✅ Connected to PostgreSQL
   Version: PostgreSQL 16.x

============================================================
TEST 3: Posts Table
============================================================
✅ Posts table exists
   Current count: 982 posts
   Posts needing details: X

============================================================
TEST 4: Update Post Details
============================================================
   Testing with post: 141080275
✅ Post updated successfully
   Title: Test Post - Phase 2 PostgreSQL Integration
   Full content length: 36 chars
   Content blocks: 2 blocks
   Images: 2 images
   Tags: 3 tags

============================================================
📊 TEST SUMMARY
============================================================
  ✅ PASS: Flag Detection
  ✅ PASS: Database Connection
  ✅ PASS: Posts Table
  ✅ PASS: Update Post Details

  Total: 4/4 tests passed

🎉 All tests passed! Phase 2 PostgreSQL integration is ready!
```

## 📝 What's Fixed

### `src/phase2_detail_extractor.py`

Now correctly updates these columns in PostgreSQL:
- `title` - Post title
- `full_content` - Extracted text from content_blocks
- `content_blocks` - Structured content as JSONB
- `published_at` - Publication timestamp
- `video_streams` - HLS streams as JSONB
- `video_subtitles` - Subtitle files as JSONB
- `video_local_paths` - Downloaded video paths
- `audios` - Audio URLs
- `audio_local_paths` - Downloaded audio paths
- `images` - Image URLs
- `image_local_paths` - Downloaded image paths
- `patreon_tags` - Post tags

### Dual Mode Behavior

When `config/use_postgresql.flag` exists:
- ✅ Saves post details to JSON (backward compatibility)
- ✅ Updates post in PostgreSQL with full extracted data
- ⚠️  If PostgreSQL update fails, continues (logs warning)

## 🔄 Next Steps

After test passes:
1. ✅ Phase 2 is ready for production use
2. ⏳ Continue with Phase 1 URL collector (FASE 2.1)
3. 🌐 Update web viewer (FASE 3)
4. 🧪 Full integration testing (FASE 4)
