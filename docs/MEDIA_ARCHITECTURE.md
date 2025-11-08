# Media Architecture - How Media Storage and Filtering Works

## Overview

The Patreon scraper system uses a three-phase approach with separate storage for media URLs and downloaded files.

---

## Three-Phase Architecture

### Phase 1: List Posts
- **Purpose:** Discover all posts for a creator
- **Output:** Basic post metadata (ID, URL, title)
- **Storage:** `data/processed/{creator_id}_posts_list.json`

### Phase 2: Extract Details
- **Purpose:** Scrape full post content, media URLs, metadata
- **Output:** Complete post data with URLs to images/audio/video
- **Storage:**
  - PostgreSQL `posts` table
  - JSON: `data/processed/{creator_id}_posts_detailed.json`

### Phase 3: Download Media
- **Purpose:** Download actual media files from URLs
- **Output:** Local media files with deduplication
- **Storage:** `data/media/{type}/{creator_id}/`

---

## Media Storage in PostgreSQL

### Schema: Posts Table

```sql
CREATE TABLE posts (
    -- Basic info
    post_id VARCHAR(255) PRIMARY KEY,
    creator_id VARCHAR(255) NOT NULL,
    source_id INTEGER NOT NULL REFERENCES creator_sources(id),
    post_url TEXT,
    title TEXT,
    full_content TEXT,

    -- Content structure
    content_blocks JSONB,  -- Text, headings, comments (NOT media)
    post_metadata JSONB,

    -- Media URLs (from Phase 2 scraper)
    images JSONB,          -- Array of image URLs
    audios JSONB,          -- Array of audio URLs
    videos JSONB,          -- Array of video URLs (Patreon-hosted)
    video_streams JSONB,   -- Video stream metadata
    video_subtitles JSONB, -- Subtitle metadata
    attachments JSONB,     -- PDF/document attachments [{filename, url}]

    -- Downloaded media paths (from Phase 3 downloader)
    image_local_paths TEXT[],  -- Relative paths to downloaded images
    audio_local_paths TEXT[],  -- Relative paths to downloaded audio
    video_local_paths TEXT[],  -- Relative paths to downloaded videos

    -- Other metadata
    published_at TIMESTAMP,
    patreon_tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);
```

### Key Points

1. **URLs vs Local Paths**
   - `images/audios/videos` (JSONB) = URLs from Patreon
   - `*_local_paths` (TEXT[]) = Actual files on disk

2. **Content Blocks ≠ Media**
   - `content_blocks` stores text structure, NOT media
   - Media is in separate columns

3. **Multi-Source Design**
   - `source_id` references `creator_sources` table
   - Supports multiple platforms (Patreon, future: YouTube, etc.)

---

## Content Blocks Structure

### What's Stored in content_blocks

```jsonb
[
  {
    "type": "paragraph",
    "text": "This is the post content..."
  },
  {
    "type": "heading_3",
    "text": "Section Heading"
  },
  {
    "type": "comment",
    "author": "username",
    "avatar_url": "https://...",
    "text": "Great post!",
    "created_at": "2024-01-15 14:30:00"
  },
  {
    "type": "comments_header",
    "count": 5
  }
]
```

### Block Types Created by Scraper

✅ **Supported:**
- `paragraph` - Post text content
- `heading_3` - Section headings
- `comment` - User comments
- `comments_header` - Comment section header

❌ **NOT Supported:**
- `image` - NOT created (images stored in `images` array)
- `audio` - NOT created (audio stored in `audios` array)
- `video` - NOT created (videos stored in `videos` array)
- `youtube_embed` - NOT created

### Why Not Store Media in content_blocks?

1. **Deduplication** - Same image used in multiple posts
2. **Download tracking** - Separate phase for downloading
3. **Storage efficiency** - Don't duplicate URLs
4. **Query performance** - Easier to filter by array columns

---

## Attachments Structure

### What are Attachments?

Attachments are downloadable files (PDFs, documents, etc.) that creators include with their posts. Unlike embedded media (images, audio, video), attachments are external files that users download separately.

### Storage Format

Attachments are stored in the `attachments` JSONB column as an array of objects:

```jsonb
[
  {
    "filename": "Guide_to_Astronomy.pdf",
    "url": "https://www.patreon.com/file/..."
  },
  {
    "filename": "Star_Chart_2024.pdf",
    "url": "https://www.patreon.com/file/..."
  }
]
```

### Schema Evolution

**Original design** (schema_v2.sql):
```sql
attachments TEXT[]  -- Simple array of filenames
```

**Current design** (after migration):
```sql
attachments JSONB  -- Structured objects with filename + URL
```

**Migration:** See `database/migrations/003_alter_attachments_to_jsonb.sql`

**Reason for change:**
- Need to store both filename AND download URL
- `text[]` insufficient for structured data
- JSONB allows flexible querying and indexing

### Extraction Process

**File:** `src/content_parser.py`

```python
def _extract_attachments(self, driver: WebDriver) -> list:
    """
    Extract PDF/document attachments from Patreon post.
    Returns: List of dicts with {filename, url}
    """
    attachments = []

    # Find attachment containers by data-tag
    containers = driver.find_elements(
        By.CSS_SELECTOR,
        '[data-tag="post-attachments"]'
    )

    for container in containers:
        # Find all attachment links
        links = container.find_elements(
            By.CSS_SELECTOR,
            'a[data-tag="post-attachment-link"]'
        )

        for link in links:
            url = link.get_attribute('href')
            filename = link.find_element(By.TAG_NAME, 'p').text.strip()

            if url:
                attachments.append({
                    'filename': filename,
                    'url': url
                })
                logger.info(f"  ✓ Found attachment: {filename}")

    return attachments
```

### Database Storage

**Phase 2 UPSERT** (`src/phase2_detail_extractor.py`):

```python
upsert_params = {
    # ... other params ...
    'attachments': json.dumps(post_data.get('attachments', [])),
}

upsert_sql = text("""
INSERT INTO posts (
    post_id, creator_id, source_id, ..., attachments, ...
) VALUES (
    :post_id, :creator_id, :source_id, ..., CAST(:attachments AS jsonb), ...
)
ON CONFLICT (post_id) DO UPDATE SET
    attachments = EXCLUDED.attachments,
    ...
""")
```

### Web Viewer Display

**Template:** `web/templates/post.html`

```html
{% if post.attachments and post.attachments|length > 0 %}
<div class="attachments-section">
    <div class="attachments-header">
        <!-- Professional document icon -->
        <svg class="attachment-icon" viewBox="0 0 24 24">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <h3>Attachments ({{ post.attachments|length }})</h3>
    </div>

    <div class="attachments-list">
        {% for attachment in post.attachments %}
        <a href="{{ attachment.url }}"
           class="attachment-item"
           target="_blank"
           download>
            <svg class="doc-icon">...</svg>
            <span class="filename">{{ attachment.filename }}</span>
            <svg class="download-icon">...</svg>
        </a>
        {% endfor %}
    </div>
</div>
{% endif %}
```

**Styling features:**
- Professional document icons (SVG)
- Hover effects for download links
- Download icon indicator
- Responsive design
- Consistent with media sections (audio, video, images)

### Index Page Counter and Filter

**Template:** `web/templates/index.html`

**Count attachments:**
```jinja2
{% set att_count = post.attachments | length if post.attachments else 0 %}
```

**Display counter with icon:**
```html
<span class="meta-icon-with-count {% if att_count > 0 %}active{% endif %}"
      title="Attachments">
    <span class="icon">
        <svg viewBox="0 0 24 24">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586..."/>
        </svg>
    </span>
    <span class="count">{{ att_count }}</span>
</span>
```

**Filter button:**
```html
<button class="content-filter-btn" id="filterAttachments">
    <span class="icon"><svg>...</svg></span>
    <span>With Attachments</span>
</button>
```

**JavaScript filter logic:**
```javascript
const contentFilters = {
    images: false,
    videos: false,
    audio: false,
    attachments: false  // NEW
};

filterAttachments.addEventListener('click', function() {
    contentFilters.attachments = !contentFilters.attachments;
    this.classList.toggle('selected');
    filterPosts();
});

// In filterPostsImmediate():
const hasAttachments = card.dataset.hasAttachments === 'true';

if (contentFilters.images || contentFilters.videos ||
    contentFilters.audio || contentFilters.attachments) {
    contentMatch = (contentFilters.images && hasImages) ||
                   (contentFilters.videos && hasVideos) ||
                   (contentFilters.audio && hasAudio) ||
                   (contentFilters.attachments && hasAttachments);
}
```

### Query Examples

**Find posts with attachments:**
```sql
SELECT post_id, title, attachments
FROM posts
WHERE attachments IS NOT NULL
  AND jsonb_array_length(attachments) > 0;
```

**Find specific attachment by filename:**
```sql
SELECT post_id, title, att->>'filename' as filename
FROM posts,
     jsonb_array_elements(attachments) as att
WHERE att->>'filename' ILIKE '%astronomy%';
```

**Count total attachments across all posts:**
```sql
SELECT COUNT(*)
FROM posts,
     jsonb_array_elements(attachments) as att;
```

---

## Media Filtering in Web Viewer

### How "With Audio" Filter Works

#### Template: index.html

```jinja2
{# 1. Count downloaded files first (most reliable) #}
{% set aud_count_local = post.audio_local_paths | length if post.audio_local_paths else 0 %}

{# 2. Fall back to URLs if no downloads #}
{% set aud_count_url = post.audios | length if post.audios else 0 %}

{# 3. Use whichever is greater #}
{% set aud_count = aud_count_local if aud_count_local > 0 else aud_count_url %}

{# 4. Only check content_blocks as last resort (old data) #}
{% if aud_count == 0 and post.content_blocks %}
    {% set aud_count = post.content_blocks | selectattr('type', 'equalto', 'audio') | list | length %}
{% endif %}
```

#### Priority Order

1. **`audio_local_paths`** - Actual downloaded files
2. **`audios`** - URLs from scraper
3. **`content_blocks`** - Legacy fallback (will be 0 for current data)

#### JavaScript Filter

```javascript
// Filter posts by "with audio"
if (hasAudioFilter) {
    cards = cards.filter(card => {
        return card.dataset.hasAudio === 'true';
    });
}
```

The `data-has-audio` attribute is set based on `aud_count > 0`.

---

## Media Download Configuration

### File: config/settings.json

```json
{
  "media": {
    "images": {
      "download_content_images": true,
      "min_size": {
        "width": 400,
        "height": 400,
        "note": "Filter out small icons/avatars (secondary filter)"
      },
      "deduplication": true,
      "note": "Scraper filters by data-media-id attribute (only content images)"
    },
    "patreon": {
      "videos": {
        "download": true,
        "quality": "best",
        "format": "mp4",
        "fallback_message": "Ver en Patreon",
        "deduplication": true
      },
      "audios": {
        "download": true,
        "format": "mp3",
        "deduplication": true
      }
    },
    "youtube": {
      "mode": "download",
      "download_if_embed_fails": false,
      "download_settings": {
        "quality": "best",
        "subtitles": ["en", "es"],
        "auto_subtitles": true,
        "format": "mp4"
      }
    },
    "deduplication": {
      "enabled": true,
      "hash_algorithm": "sha256",
      "use_database": true
    }
  }
}
```

### Image Filtering

The scraper uses two filters to exclude avatars/thumbnails:

1. **Primary:** HTML `data-media-id` attribute
   - Only scrapes `<img>` tags with `data-media-id`
   - Patreon uses this for content images, not UI elements

2. **Secondary:** `min_size` dimensions
   - Filters out small images (< 400x400)
   - Catches any remaining icons/avatars

**Removed settings (redundant):**
- ❌ `skip_avatars` - Redundant (handled by data-media-id)
- ❌ `skip_covers` - Redundant (handled by data-media-id)
- ❌ `skip_thumbnails` - Redundant (handled by data-media-id)

---

## File Structure

```
data/
├── processed/
│   ├── astrobymax_posts_list.json      # Phase 1 output
│   └── astrobymax_posts_detailed.json  # Phase 2 output
│
└── media/
    ├── images/
    │   └── astrobymax/
    │       ├── image_001.jpg
    │       ├── image_002.png
    │       └── ...
    ├── audio/
    │   └── astrobymax/
    │       ├── audio_001.mp3
    │       ├── audio_002.m4a
    │       └── ...
    └── videos/
        └── astrobymax/
            ├── video_001.mp4
            └── ...
```

### Path Storage

**In database:**
```sql
SELECT audio_local_paths FROM posts WHERE post_id = '12345678';

-- Result:
{
  "audio/astrobymax/audio_001.mp3",
  "audio/astrobymax/audio_002.m4a"
}
```

**Relative to:** `data/media/`

**Full path:** `data/media/audio/astrobymax/audio_001.mp3`

---

## Deduplication System

### How It Works

1. **Download media file**
2. **Calculate SHA256 hash** of file content
3. **Check database** for existing hash
4. **If duplicate:** Skip download, reuse existing file
5. **If new:** Save file, store hash in database

### Schema: media_hashes

```sql
CREATE TABLE media_hashes (
    id SERIAL PRIMARY KEY,
    hash VARCHAR(64) UNIQUE NOT NULL,
    media_type VARCHAR(50),  -- 'image', 'audio', 'video'
    file_path TEXT NOT NULL,
    creator_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Example

```
Post A: https://patreon.com/file/12345.mp3
Post B: https://patreon.com/file/67890.mp3  (same file, different URL)

Download Post A:
  - Calculate hash: a1b2c3d4...
  - Not in database
  - Save: audio/astrobymax/audio_001.mp3
  - Store hash

Download Post B:
  - Calculate hash: a1b2c3d4...
  - Found in database!
  - Reuse: audio/astrobymax/audio_001.mp3
  - Don't download again
```

---

## Viewer Implementation

### Load Posts from PostgreSQL

```python
def load_all_posts():
    """Load all posts from PostgreSQL"""
    with engine.connect() as conn:
        query = text("""
            SELECT
                post_id,
                creator_id,
                post_url,
                title,
                full_content,
                content_blocks,
                post_metadata,
                published_at,
                images,
                audios,
                videos,
                image_local_paths,
                audio_local_paths,
                video_local_paths,
                video_streams,
                video_subtitles,
                patreon_tags
            FROM posts
            WHERE deleted_at IS NULL
            ORDER BY post_id DESC
        """)

        result = conn.execute(query)
        rows = result.fetchall()

        posts = []
        for row in rows:
            post = {
                'post_id': row[0],
                'creator_id': row[1],
                # ... map all columns
                'image_local_paths': row[11] if row[11] else [],
                'audio_local_paths': row[12] if row[12] else [],
                'video_local_paths': row[13] if row[13] else [],
            }
            posts.append(post)

        return posts
```

### Count Media (Python - Single Post View)

```python
# Get media arrays
image_local = post.get('image_local_paths') or []
audio_local = post.get('audio_local_paths') or []
video_local = post.get('video_local_paths') or []

# Count downloaded files first, fall back to URLs
image_count = len(image_local) if image_local else len(post.get('images') or [])
audio_count = len(audio_local) if audio_local else len(post.get('audios') or [])
video_count = len(video_local) if video_local else len(post.get('videos') or [])

# Legacy fallback for old data
if not image_count and content_blocks:
    image_count = count_blocks('image')  # Will be 0 for current data
if not audio_count and content_blocks:
    audio_count = count_blocks('audio')  # Will be 0 for current data
if not video_count and content_blocks:
    video_count = count_blocks('video') + count_blocks('youtube_embed')
```

### Filter Extensions (Python)

```python
def filter_by_extension(values, extensions):
    """Filter paths by file extension"""
    if not values:
        return []

    cleaned = []
    for entry in values:
        if not entry:
            continue
        entry_str = str(entry).replace('\\', '/')
        if any(entry_str.lower().endswith(ext) for ext in extensions):
            cleaned.append(entry_str)

    return cleaned

# Usage
audio_paths = filter_by_extension(
    post.get('audio_local_paths'),
    {'.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus'}
)
```

---

## Common Issues and Solutions

### Issue: Filter shows 0 posts but media exists

**Diagnosis:**
```bash
# Check database
psql -U patreon_user -d alejandria -c "
SELECT COUNT(*)
FROM posts
WHERE creator_id = 'astrobymax'
  AND audio_local_paths IS NOT NULL;
"

# Check template logic
# Look for: content_blocks | selectattr('type', 'equalto', 'audio')
# This is WRONG - should use audio_local_paths
```

**Solution:**
Update template to use `*_local_paths` arrays, not `content_blocks`.

### Issue: Duplicate downloads

**Diagnosis:**
```bash
# Check deduplication is enabled
cat config/settings.json | grep -A 5 deduplication

# Check hash table
psql -U patreon_user -d alejandria -c "
SELECT COUNT(*) FROM media_hashes;
"
```

**Solution:**
Ensure `settings.json` has `deduplication.enabled: true`.

### Issue: Missing source_id in UPSERT

**Diagnosis:**
```
ERROR: null value in column "source_id" violates not-null constraint
```

**Solution:**
Always resolve `creator_id` → `source_id` before UPSERT:

```python
result = conn.execute(text("""
    SELECT cs.id
    FROM creator_sources cs
    WHERE cs.platform = 'patreon'
      AND cs.platform_id = :creator_id
"""), {'creator_id': creator_id})

source_id = result.fetchone()[0]
```

---

## Testing Media Filters

### Test Suite

```bash
# 1. Run diagnostic
python3 tools/diagnose_phase2_data.py

# 2. Check audio filter
# - Open http://localhost:5000/
# - Click "with audio"
# - Verify count matches database

# 3. Check image filter
# - Click "with images"
# - Verify count matches database

# 4. Check video filter
# - Click "with videos"
# - Verify count matches database
```

### Expected Results (astrobymax)

- **With audio:** 13 posts
- **With images:** 51 posts
- **With videos:** Varies (check database)

---

## Related Documentation

- `BUGFIXES_PHASE2.md` - Bug fixes for Phase 2
- `schema/schema_v2.sql` - Database schema
- `README.md` - Project overview
