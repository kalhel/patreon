# Phase 2 Bug Fixes - Audio/Image/Video Filter Issues

## Date: 2025-11-08

---

## BUG #1: Posts Not Inserting into PostgreSQL (Phase 2 UPSERT)

### Symptom
- Phase 2 completed successfully (80 posts processed for astrobymax)
- Status table showed `phase2_status = 'completed'`
- BUT: `SELECT COUNT(*) FROM posts WHERE creator_id = 'astrobymax'` returned **0**
- Posts existed in JSON but not in database

### Error Message
```
psycopg2.errors.NotNullViolation: null value in column "source_id" of relation "posts" violates not-null constraint
```

### Root Cause
The Phase 2 UPSERT SQL was missing the `source_id` column:
- Table `posts` has two NOT NULL columns: `creator_id` (VARCHAR) and `source_id` (INTEGER FK)
- UPSERT only included `creator_id`, not `source_id`
- `source_id` references `creator_sources.id` (multi-source architecture)

### Solution
**File:** `src/phase2_detail_extractor.py`

Added source_id resolution before UPSERT:

```python
# Resolve creator_id to source_id
result = conn.execute(text("""
    SELECT cs.id
    FROM creator_sources cs
    WHERE cs.platform = 'patreon'
      AND cs.platform_id = :creator_id
"""), {'creator_id': creator_id})

row = result.fetchone()
if not row:
    raise ValueError(f"Could not resolve creator '{creator_id}' to source_id")

source_id = row[0]
```

Then included `source_id` in INSERT:

```python
INSERT INTO posts (
    post_id, creator_id, source_id, post_url, title, full_content,
    ...
) VALUES (
    :post_id, :creator_id, :source_id, :post_url, :title, :full_content,
    ...
)
```

### Commits
- `eacf7ea` - FIX: Add missing source_id to Phase 2 UPSERT

---

## BUG #2: "With Audio" Filter Shows 0 Posts (Index Page)

### Symptom
- Audio files downloaded correctly to `data/media/audio/astrobymax/`
- PostgreSQL has `audio_local_paths` populated (13 posts)
- Clicking "with audio" filter shows **0 posts**
- Individual post view shows audio correctly

### Root Cause
The `index.html` template was counting media incorrectly:

**Line 1518 (WRONG):**
```jinja2
{% set aud_count = post.content_blocks | selectattr('type', 'equalto', 'audio') | list | length %}
```

This looks for blocks with `type='audio'` in `content_blocks` JSONB.

**BUT:** The scraper doesn't create blocks with `type='audio'`. It only creates:
- `paragraph` - Text content
- `heading_3` - Headings
- `comment` - Comments
- `comments_header` - Comment section header

**Proof:**
```sql
SELECT DISTINCT jsonb_array_elements(content_blocks)->>'type' as block_type
FROM posts WHERE creator_id = 'astrobymax';

   block_type
-----------------
 paragraph
 comment
 heading_3
 comments_header
```

No `audio`, `image`, or `video` blocks exist!

### Solution
**File:** `web/templates/index.html` (lines 1513-1537)

Changed to prioritize actual downloaded media:

```jinja2
{# Count media using downloaded files first (most reliable), then URLs, then content_blocks (old data) #}
{% set img_count_local = post.image_local_paths | length if post.image_local_paths else 0 %}
{% set aud_count_local = post.audio_local_paths | length if post.audio_local_paths else 0 %}
{% set vid_count_local = post.video_local_paths | length if post.video_local_paths else 0 %}

{% set img_count_url = post.images | length if post.images else 0 %}
{% set aud_count_url = post.audios | length if post.audios else 0 %}
{% set vid_count_url = post.videos | length if post.videos else 0 %}

{% set img_count = img_count_local if img_count_local > 0 else img_count_url %}
{% set aud_count = aud_count_local if aud_count_local > 0 else aud_count_url %}
{% set vid_count = vid_count_local if vid_count_local > 0 else vid_count_url %}

{# Fall back to content_blocks only if no media arrays (old data compatibility) #}
{% if img_count == 0 and post.content_blocks %}
    {% set img_count = post.content_blocks | selectattr('type', 'equalto', 'image') | list | length %}
{% endif %}
{% if aud_count == 0 and post.content_blocks %}
    {% set aud_count = post.content_blocks | selectattr('type', 'equalto', 'audio') | list | length %}
{% endif %}
{% if vid_count == 0 and post.content_blocks %}
    {% set vid_count = (post.content_blocks | selectattr('type', 'equalto', 'video') | list | length) + (post.content_blocks | selectattr('type', 'equalto', 'youtube_embed') | list | length) %}
{% endif %}
```

**Priority:**
1. **`*_local_paths` arrays** - Actual downloaded files (most reliable)
2. **`images/audios/videos` arrays** - URLs from scraper
3. **`content_blocks` filtering** - Only for old data compatibility

### Also Fixed
**File:** `web/viewer.py` (lines 524-546)

Single post view had same issue. Applied same fix:

```python
# Priority: Use downloaded media paths first (most reliable), then URLs, then content_blocks
image_local = post.get('image_local_paths') or []
audio_local = post.get('audio_local_paths') or []
video_local = post.get('video_local_paths') or []

# Count actual downloaded media
image_count = len(image_local) if image_local else len(post.get('images') or [])
audio_count = len(audio_local) if audio_local else len(post.get('audios') or [])
video_count = len(video_local) if video_local else len(post.get('videos') or [])

# If no media arrays exist, fall back to counting content_blocks (old data)
if not image_count and content_blocks:
    image_count = count_blocks('image')
if not audio_count and content_blocks:
    audio_count = count_blocks('audio')
if not video_count and content_blocks:
    video_count = count_blocks('video') + count_blocks('youtube_embed')
```

### Commits
- `73972d9` - FIX: Use media arrays instead of content_blocks for counting (viewer.py)
- `f49bde2` - FIX: Index template - use media arrays instead of content_blocks

---

## Database Schema Reference

### Posts Table - Media Columns

```sql
-- URL arrays (JSONB) - from scraper
images           JSONB      -- Array of image URLs from Patreon
audios           JSONB      -- Array of audio URLs from Patreon
videos           JSONB      -- Array of video URLs from Patreon

-- Downloaded file paths (TEXT[]) - from Phase 3 downloader
image_local_paths   TEXT[]  -- Array of relative paths to downloaded images
audio_local_paths   TEXT[]  -- Array of relative paths to downloaded audio
video_local_paths   TEXT[]  -- Array of relative paths to downloaded videos

-- Content structure (JSONB)
content_blocks   JSONB      -- Array of content blocks (paragraph, heading, comment)
```

### Content Blocks Structure

```jsonb
[
  {
    "type": "paragraph",
    "text": "Post content..."
  },
  {
    "type": "heading_3",
    "text": "Section Heading"
  },
  {
    "type": "comment",
    "author": "username",
    "text": "Comment text...",
    "created_at": "2024-01-15"
  }
]
```

**Block types created by scraper:**
- `paragraph` - Text content
- `heading_3` - Section headings
- `comment` - User comments
- `comments_header` - Comment section header

**Block types NOT created:**
- ❌ `image` - Not used
- ❌ `audio` - Not used
- ❌ `video` - Not used
- ❌ `youtube_embed` - Not used

Media is stored in separate arrays (`images`, `audios`, `videos`, `*_local_paths`), not in `content_blocks`.

---

## How Media Counting Works Now

### Priority Order (Most Reliable → Least Reliable)

1. **Downloaded files** (`*_local_paths` arrays)
   - Actual files on disk
   - Populated by Phase 3 downloader
   - Most reliable source of truth

2. **URLs** (`images/audios/videos` JSONB arrays)
   - URLs scraped from Patreon
   - Populated by Phase 2 scraper
   - Files may not be downloaded yet

3. **Content blocks** (legacy fallback)
   - Only for old data that doesn't have media arrays
   - Not used for current scraping

### Example: Counting Audio

```python
# 1. Check downloaded files first
audio_local = post.get('audio_local_paths') or []
if audio_local:
    audio_count = len(audio_local)
else:
    # 2. Fall back to URLs
    audios = post.get('audios') or []
    audio_count = len(audios)

# 3. Last resort: content_blocks (for old data)
if not audio_count and content_blocks:
    audio_count = count_blocks('audio')  # Will be 0 for current data
```

---

## Testing

### Verify Audio Filter Works

```bash
# 1. Check posts with audio in database
psql -U patreon_user -d alejandria -c "
SELECT post_id,
       array_length(audio_local_paths, 1) as audio_count
FROM posts
WHERE creator_id = 'astrobymax'
  AND audio_local_paths IS NOT NULL
ORDER BY post_id;
"

# Expected: 13 posts with audio_count > 0

# 2. Check downloaded audio files
ls -la data/media/audio/astrobymax/

# Expected: ~13 audio files (.mp3, .m4a, etc.)

# 3. Test web viewer
# - Open http://localhost:5000/
# - Click "with audio" filter
# - Should show 13 posts for astrobymax
```

### Verify Image Filter Works

```bash
# 1. Check posts with images in database
psql -U patreon_user -d alejandria -c "
SELECT COUNT(*)
FROM posts
WHERE creator_id = 'astrobymax'
  AND array_length(image_local_paths, 1) > 0;
"

# Expected: ~51 posts

# 2. Check downloaded images
ls -la data/media/images/astrobymax/ | wc -l

# 3. Test web viewer
# - Click "with images" filter
# - Should show ~51 posts
```

---

## Diagnostic Tools

### Script: `tools/diagnose_phase2_data.py`

Comprehensive diagnostic that compares JSON vs PostgreSQL data:

```bash
python3 tools/diagnose_phase2_data.py
```

**Checks:**
1. Posts in JSON vs PostgreSQL
2. Media counts (audio/images/videos)
3. How viewer.py reads data
4. Different SQL filter conditions
5. Downloaded media files in filesystem
6. Missing data analysis

### Script: `tools/check_audio_issue.py`

Quick audio-specific diagnostic:

```bash
python3 tools/check_audio_issue.py
```

Shows exactly how viewer counts audio for first few posts.

---

## Lessons Learned

1. **Always check both Python and template code** when fixing display issues
   - Fixed viewer.py but forgot index.html template
   - Both need to use same logic

2. **Don't assume content_blocks contains media**
   - Scraper stores media in separate arrays
   - content_blocks only has text/comments

3. **Prioritize actual downloaded files over URLs**
   - `*_local_paths` = truth on disk
   - URLs may be broken/changed

4. **Use diagnostic scripts before fixing**
   - Prevents breaking things further
   - Shows exact state of data

---

## Related Files

- `src/phase2_detail_extractor.py` - Phase 2 scraper (UPSERT logic)
- `web/viewer.py` - Single post view (media counting)
- `web/templates/index.html` - Post list view (media counting)
- `web/templates/post.html` - Single post template
- `tools/diagnose_phase2_data.py` - Comprehensive diagnostic
- `tools/validate_phase2_upsert.py` - Pre-commit validation
- `schema/schema_v2.sql` - Database schema
