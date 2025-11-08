# Settings Configuration Guide

## File: config/settings.json

This file controls media download behavior, scraping parameters, and system configuration.

---

## Media Settings

### Images

```json
{
  "media": {
    "images": {
      "download_content_images": true,
      "min_size": {
        "width": 400,
        "height": 400,
        "note": "Filter out small icons/avatars (secondary filter after data-media-id)"
      },
      "deduplication": true,
      "note": "Scraper filters by data-media-id attribute (only content images), min_size is secondary filter"
    }
  }
}
```

#### Options

- **`download_content_images`** (boolean)
  - `true`: Download images from posts
  - `false`: Skip image downloads
  - **Default:** `true`
  - **Note:** Only downloads images with `data-media-id` attribute

- **`min_size.width`** (integer)
  - Minimum image width in pixels
  - **Default:** `400`
  - **Purpose:** Filter out small icons/avatars (secondary filter)

- **`min_size.height`** (integer)
  - Minimum image height in pixels
  - **Default:** `400`
  - **Purpose:** Filter out small icons/avatars (secondary filter)

- **`deduplication`** (boolean)
  - `true`: Use hash-based deduplication (skip duplicate images)
  - `false`: Download all images even if duplicate
  - **Default:** `true`
  - **Recommended:** `true` (saves bandwidth and storage)

#### Image Filtering - Two-Stage Process

**Stage 1: HTML Attribute (Primary Filter)**
- Scraper only selects `<img>` tags with `data-media-id` attribute
- Patreon uses this for content images (not UI elements)
- Automatically excludes:
  - User avatars
  - Cover images
  - Thumbnails
  - UI icons

**Stage 2: Size Filter (Secondary Filter)**
- Applied after HTML filter
- Catches any remaining small images
- Images below `min_size` are discarded

**Example:**
```html
<!-- ✅ Downloaded: Has data-media-id, is content image -->
<img data-media-id="12345678" src="https://..." width="1200" height="800">

<!-- ❌ Skipped: No data-media-id (avatar) -->
<img src="https://..." class="avatar" width="100" height="100">

<!-- ❌ Skipped: Has data-media-id but too small -->
<img data-media-id="87654321" src="https://..." width="200" height="200">
```

---

### Patreon Videos

```json
{
  "media": {
    "patreon": {
      "videos": {
        "download": true,
        "quality": "best",
        "format": "mp4",
        "fallback_message": "Ver en Patreon",
        "deduplication": true,
        "note": "Hash-based deduplication prevents downloading identical videos"
      }
    }
  }
}
```

#### Options

- **`download`** (boolean)
  - `true`: Download Patreon-hosted videos
  - `false`: Only save video metadata (no download)
  - **Default:** `true`

- **`quality`** (string)
  - Video quality preference
  - **Options:** `"best"`, `"720p"`, `"480p"`, `"360p"`
  - **Default:** `"best"`
  - **Note:** Falls back to best available if requested quality not found

- **`format`** (string)
  - Video container format
  - **Options:** `"mp4"`, `"webm"`
  - **Default:** `"mp4"`
  - **Recommended:** `"mp4"` (best compatibility)

- **`fallback_message`** (string)
  - Message shown in viewer if video can't be embedded
  - **Default:** `"Ver en Patreon"`
  - **Note:** Provides link back to original post

- **`deduplication`** (boolean)
  - `true`: Skip downloading duplicate videos (same content, different URLs)
  - `false`: Download all videos
  - **Default:** `true`

---

### Patreon Audio

```json
{
  "media": {
    "patreon": {
      "audios": {
        "download": true,
        "format": "mp3",
        "deduplication": true,
        "note": "Hash-based deduplication prevents downloading identical audio files"
      }
    }
  }
}
```

#### Options

- **`download`** (boolean)
  - `true`: Download audio files
  - `false`: Only save audio URLs
  - **Default:** `true`

- **`format`** (string)
  - Audio format preference
  - **Options:** `"mp3"`, `"m4a"`, `"aac"`, `"original"`
  - **Default:** `"mp3"`
  - **Note:** Converts to specified format if possible

- **`deduplication`** (boolean)
  - `true`: Skip downloading duplicate audio files
  - `false`: Download all audio files
  - **Default:** `true`

---

### YouTube Videos

```json
{
  "media": {
    "youtube": {
      "mode": "download",
      "download_if_embed_fails": false,
      "download_settings": {
        "quality": "best",
        "subtitles": ["en", "es"],
        "auto_subtitles": true,
        "format": "mp4"
      },
      "note": "mode: 'embed' (fast, no download) or 'download' (slow, requires yt-dlp)"
    }
  }
}
```

#### Options

- **`mode`** (string)
  - `"embed"`: Show YouTube player in viewer (fast, no download)
  - `"download"`: Download YouTube videos locally (slow, requires yt-dlp)
  - **Default:** `"download"`
  - **Recommendation:**
    - Use `"embed"` for faster scraping
    - Use `"download"` for archival purposes

- **`download_if_embed_fails`** (boolean)
  - `true`: Fall back to download if embed doesn't work
  - `false`: Don't download even if embed fails
  - **Default:** `false`
  - **Note:** Only applies when `mode: "embed"`

- **`download_settings.quality`** (string)
  - **Options:** `"best"`, `"1080p"`, `"720p"`, `"480p"`
  - **Default:** `"best"`

- **`download_settings.subtitles`** (array of strings)
  - Language codes for subtitles to download
  - **Example:** `["en", "es", "fr"]`
  - **Default:** `["en", "es"]`

- **`download_settings.auto_subtitles`** (boolean)
  - `true`: Download auto-generated subtitles if manual not available
  - `false`: Only download manual subtitles
  - **Default:** `true`

- **`download_settings.format`** (string)
  - **Options:** `"mp4"`, `"webm"`, `"mkv"`
  - **Default:** `"mp4"`

#### Requirements

- **Mode: "embed"** - No requirements
- **Mode: "download"** - Requires `yt-dlp` installed:
  ```bash
  pip install yt-dlp
  ```

---

### Global Deduplication

```json
{
  "media": {
    "deduplication": {
      "enabled": true,
      "hash_algorithm": "sha256",
      "use_database": true,
      "note": "Prevent downloading same file twice using SHA256 hash"
    }
  }
}
```

#### Options

- **`enabled`** (boolean)
  - `true`: Enable global deduplication across all media types
  - `false`: Disable deduplication
  - **Default:** `true`
  - **Recommendation:** Keep enabled to save bandwidth/storage

- **`hash_algorithm`** (string)
  - Hashing algorithm for file content
  - **Options:** `"sha256"`, `"md5"`, `"sha1"`
  - **Default:** `"sha256"`
  - **Note:** SHA256 is more secure but slightly slower

- **`use_database`** (boolean)
  - `true`: Store hashes in PostgreSQL (faster, persistent)
  - `false`: Store hashes in memory only (lost on restart)
  - **Default:** `true`
  - **Recommendation:** Use database for production

#### How Deduplication Works

1. Media file is about to be downloaded
2. Calculate hash of file content
3. Query `media_hashes` table for existing hash
4. If found: Reuse existing file, skip download
5. If not found: Download file, store hash in database

**Example:**
```
Post A: https://cdn.patreon.com/audio/12345.mp3
Post B: https://cdn.patreon.com/audio/67890.mp3  (same file, different URL)

Processing Post A:
  Hash: a1b2c3d4e5f6...
  Not in database → Download
  Save as: audio/creator/audio_001.mp3
  Store hash in DB

Processing Post B:
  Hash: a1b2c3d4e5f6...
  Found in database! → Reuse audio_001.mp3
  Don't download
```

---

## Scraping Settings

```json
{
  "scraping": {
    "max_retries": 3,
    "retry_delay": 60,
    "timeout": 300,
    "headless": true
  }
}
```

#### Options

- **`max_retries`** (integer)
  - Number of times to retry failed requests
  - **Default:** `3`
  - **Range:** `0-10`

- **`retry_delay`** (integer)
  - Seconds to wait between retries
  - **Default:** `60`
  - **Note:** Helps avoid rate limiting

- **`timeout`** (integer)
  - Seconds before request times out
  - **Default:** `300` (5 minutes)
  - **Note:** Increase for slow connections

- **`headless`** (boolean)
  - `true`: Run browser in headless mode (no GUI)
  - `false`: Show browser window (debugging)
  - **Default:** `true`
  - **Recommendation:**
    - Use `true` for production
    - Use `false` for debugging scraper issues

---

## Celery Settings (Disabled by Default)

```json
{
  "celery": {
    "enabled": false,
    "broker": "redis://localhost:6379/0",
    "workers": {
      "phase1": 2,
      "phase2": 1,
      "phase3": 2
    },
    "note": "Celery queues for production - disabled for local development"
  }
}
```

#### Options

- **`enabled`** (boolean)
  - `true`: Use Celery for distributed task processing
  - `false`: Run tasks synchronously (local development)
  - **Default:** `false`
  - **Note:** Requires Redis/RabbitMQ installed

- **`broker`** (string)
  - Message broker URL
  - **Examples:**
    - `"redis://localhost:6379/0"`
    - `"amqp://guest@localhost//"`
  - **Default:** `"redis://localhost:6379/0"`

- **`workers.phase1`** (integer)
  - Number of workers for Phase 1 (post listing)
  - **Default:** `2`

- **`workers.phase2`** (integer)
  - Number of workers for Phase 2 (detail extraction)
  - **Default:** `1`
  - **Note:** Keep low to avoid rate limiting

- **`workers.phase3`** (integer)
  - Number of workers for Phase 3 (media download)
  - **Default:** `2`

#### When to Enable Celery

- ✅ **Enable if:**
  - Scraping many creators concurrently
  - Need to distribute work across multiple machines
  - Want background task processing

- ❌ **Keep disabled if:**
  - Local development
  - Single-creator scraping
  - Simplicity preferred over scalability

---

## Configuration Examples

### Conservative Settings (Low Bandwidth)

```json
{
  "media": {
    "images": {
      "download_content_images": true,
      "min_size": {
        "width": 800,
        "height": 800
      },
      "deduplication": true
    },
    "patreon": {
      "videos": {
        "download": false,
        "quality": "480p",
        "format": "mp4",
        "deduplication": true
      },
      "audios": {
        "download": true,
        "format": "mp3",
        "deduplication": true
      }
    },
    "youtube": {
      "mode": "embed"
    }
  }
}
```

**Best for:**
- Limited bandwidth
- Storage constraints
- Faster scraping

### Archival Settings (Maximum Quality)

```json
{
  "media": {
    "images": {
      "download_content_images": true,
      "min_size": {
        "width": 200,
        "height": 200
      },
      "deduplication": true
    },
    "patreon": {
      "videos": {
        "download": true,
        "quality": "best",
        "format": "mp4",
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
      "download_settings": {
        "quality": "best",
        "subtitles": ["en", "es", "fr", "de"],
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

**Best for:**
- Long-term archival
- Maximum quality preservation
- Complete content backup

### Development Settings (Fast Testing)

```json
{
  "media": {
    "images": {
      "download_content_images": false
    },
    "patreon": {
      "videos": {
        "download": false
      },
      "audios": {
        "download": false
      }
    },
    "youtube": {
      "mode": "embed"
    }
  },
  "scraping": {
    "max_retries": 1,
    "retry_delay": 5,
    "timeout": 60,
    "headless": false
  }
}
```

**Best for:**
- Testing scraper logic
- Debugging issues
- Quick iteration

---

## Environment Variables

Settings that should be in `.env` (NOT in `settings.json`):

```bash
# Database
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=alejandria
DB_USER=patreon_user
DB_PASSWORD=your_password_here

# Scraping (optional)
SELENIUM_DRIVER=chrome
SELENIUM_HEADLESS=true

# Celery (if enabled)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## Validating Configuration

### Check Settings File

```bash
# Validate JSON syntax
python3 -m json.tool config/settings.json

# Expected: Pretty-printed JSON (no errors)
```

### Test Media Download

```bash
# Test image download
python3 -c "
import json
with open('config/settings.json') as f:
    settings = json.load(f)
print('Images enabled:', settings['media']['images']['download_content_images'])
print('Min size:', settings['media']['images']['min_size'])
"

# Expected: Shows current settings
```

---

## Common Mistakes

### ❌ Storing Secrets in settings.json

**Wrong:**
```json
{
  "database": {
    "password": "my_password"
  }
}
```

**Right:**
```bash
# In .env file
DB_PASSWORD=my_password
```

### ❌ Disabling Deduplication

**Wrong:**
```json
{
  "media": {
    "deduplication": {
      "enabled": false
    }
  }
}
```

**Why wrong:**
- Downloads same file multiple times
- Wastes bandwidth and storage
- Slower scraping

**Right:**
```json
{
  "media": {
    "deduplication": {
      "enabled": true,
      "use_database": true
    }
  }
}
```

### ❌ Setting min_size Too High

**Wrong:**
```json
{
  "media": {
    "images": {
      "min_size": {
        "width": 2000,
        "height": 2000
      }
    }
  }
}
```

**Why wrong:**
- Filters out many legitimate images
- Loses content

**Right:**
```json
{
  "media": {
    "images": {
      "min_size": {
        "width": 400,
        "height": 400
      }
    }
  }
}
```

---

## Updating Settings

### Safe Update Process

1. **Backup current settings:**
   ```bash
   cp config/settings.json config/settings.json.backup
   ```

2. **Edit settings:**
   ```bash
   nano config/settings.json
   ```

3. **Validate JSON:**
   ```bash
   python3 -m json.tool config/settings.json > /dev/null && echo "Valid JSON"
   ```

4. **Restart services:**
   ```bash
   # If Flask viewer is running
   Ctrl+C
   python3 web/viewer.py

   # If Celery is running
   pkill -f celery
   celery -A src.celery_app worker
   ```

5. **Test changes:**
   - Run Phase 2 on test creator
   - Verify media downloads correctly
   - Check web viewer

---

## Related Documentation

- `MEDIA_ARCHITECTURE.md` - How media storage works
- `BUGFIXES_PHASE2.md` - Common issues and fixes
- `README.md` - Project overview
