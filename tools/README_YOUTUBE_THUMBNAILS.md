# YouTube Thumbnail Re-processing Tools

These tools help you update YouTube thumbnails for existing posts using the new intelligent thumbnail processor.

## Overview

The new thumbnail processor (added to `content_parser.py`) automatically finds the best YouTube thumbnail during scraping by:
- Testing multiple thumbnail sources (hqdefault, mqdefault, frames 1-3, maxresdefault)
- Detecting and skipping black/dark thumbnails
- Saving the best thumbnail in the `best_thumbnail` field

**Problem:** Existing posts scraped before this update may have black thumbnails.
**Solution:** Use these tools to re-scrape only posts with YouTube videos.

---

## Tool 1: Find YouTube Posts

**Script:** `tools/find_youtube_posts.py`

Scans your Firebase database and identifies all posts containing YouTube videos.

### Usage

```bash
# Find all posts with YouTube videos
python tools/find_youtube_posts.py

# Find YouTube posts for specific creator
python tools/find_youtube_posts.py --creator headonhistory

# Save post IDs to file
python tools/find_youtube_posts.py --output youtube_posts.txt

# Generate commands for manual re-scraping
python tools/find_youtube_posts.py --generate-command
```

### Example Output

```
🔍 Scanning for posts with YouTube videos...

📊 Summary:
   Total posts scanned: 450
   Posts with YouTube: 127
   Percentage: 28.2%

📹 Posts with YouTube videos:

   headonhistory: 45 posts
   horoiproject: 62 posts
   astrobymax: 20 posts

💾 Saved 127 post IDs to: youtube_posts.txt
```

---

## Tool 2: Re-scrape YouTube Posts

**Script:** `tools/rescrape_youtube_posts.py`

Automatically re-scrapes posts with YouTube videos to update their thumbnails.

### Usage

```bash
# Re-scrape all posts with YouTube videos
python tools/rescrape_youtube_posts.py --all

# Re-scrape for specific creator only
python tools/rescrape_youtube_posts.py --creator headonhistory

# Re-scrape from saved file
python tools/rescrape_youtube_posts.py --file youtube_posts.txt

# Limit number of posts (useful for testing)
python tools/rescrape_youtube_posts.py --all --limit 10

# Dry run (see what would happen without doing it)
python tools/rescrape_youtube_posts.py --all --dry-run

# Show browser (for debugging)
python tools/rescrape_youtube_posts.py --all --no-headless
```

### Example Output

```
🔍 Finding posts with YouTube videos...

📊 Found 127 posts with YouTube videos
🔐 Authenticating with Patreon...
✅ Authentication successful

🚀 Re-scraping 127 posts...

[1/127] Processing post 98765432...
🔄 Re-scraping post 98765432 (headonhistory)...
✅ Updated 2 YouTube thumbnail(s)

[2/127] Processing post 98765433...
🔄 Re-scraping post 98765433 (headonhistory)...
✅ Updated 1 YouTube thumbnail(s)

...

============================================================
📊 Re-scraping Summary:
   ✅ Successful: 125
   ❌ Failed: 2
   📝 Total: 127
============================================================
```

---

## Recommended Workflow

### Option A: Re-scrape Everything (Safest)

```bash
# 1. Do a dry run first to see what would happen
python tools/rescrape_youtube_posts.py --all --dry-run

# 2. Re-scrape all YouTube posts
python tools/rescrape_youtube_posts.py --all
```

### Option B: Re-scrape One Creator at a Time

```bash
# Process one creator
python tools/rescrape_youtube_posts.py --creator headonhistory

# Then another
python tools/rescrape_youtube_posts.py --creator horoiproject
```

### Option C: Test First, Then Batch

```bash
# 1. Test with 5 posts
python tools/rescrape_youtube_posts.py --all --limit 5

# 2. Check if thumbnails look better in the web viewer

# 3. Process everything
python tools/rescrape_youtube_posts.py --all
```

---

## What Gets Updated?

When you re-scrape a post:
- **Updated:** `content_blocks` with new `best_thumbnail` field for YouTube embeds
- **Preserved:** All other data (title, content, images, audio, comments, etc.)
- **Effect:** Next time you view the post, it uses the better thumbnail

---

## Performance Notes

- **Speed:** ~5-10 seconds per post (depends on page load time)
- **127 posts:** ~10-20 minutes total
- **Runs in headless mode** by default (faster, no window)
- **Safe:** Only updates posts, doesn't delete anything

---

## Troubleshooting

### Script can't find posts
```bash
# Make sure you're in the project root
cd /path/to/patreon

# Check Firebase connection
python tools/find_youtube_posts.py
```

### Authentication fails
```bash
# Check credentials.json
cat config/credentials.json

# Try with visible browser
python tools/rescrape_youtube_posts.py --all --no-headless
```

### Some posts still have black thumbnails
This can happen if:
1. **All available thumbnails are black** - Some videos genuinely have dark intros for all frames
2. **Thumbnail doesn't exist** - Very old or deleted videos
3. **Network error** - Thumbnail download failed

The processor tries multiple sources, but if all fail, it falls back to `hqdefault.jpg`.

---

## Future Posts

All newly scraped posts will automatically get the best thumbnail - you only need to run these tools once for existing posts.
