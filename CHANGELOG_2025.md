# Changelog 2025

## 2025-11-08 - Media & Content Improvements

### Attachments Feature Complete
**Files**: `web/viewer.py`, `web/templates/post.html`, `web/templates/index.html`

- ✅ Added attachments support throughout the application
- ✅ Attachments display at bottom of posts (before comments)
- ✅ File-type-specific icons (PDF, DOC, TXT, generic)
- ✅ Attachment counter in post header with anchor navigation
- ✅ Removed "With" prefix from filter labels (cleaner UI)

### Original Filenames for Downloads
**Files**: `web/viewer.py`, `web/templates/post.html`

**Problem**: All media downloaded with hash-based names (e.g., `abc123_456789.jpg`)

**Solution**:
- Added `?original=filename.ext` query parameter support in `/media/` endpoint
- Uses `Content-Disposition` header to suggest original filename on download
- Maintains hash-based storage for deduplication
- Users download files with recognizable names

**Implementation**:
```python
# Server stores: images/creator/abc123_456789.jpg
# User downloads: photo.jpg (extracted from Patreon URL)
```

**Applies to**: Images, videos, audios, attachments

### Content Parser Improvements
**File**: `src/content_parser.py`

#### Fix 1: Overly Aggressive YouTube Filter
**Problem**: Posts mentioning "YouTube" had entire paragraphs deleted

**Example**: Skyscript post 141803080 lost paragraph "...the full video of his presentation (now on YouTube)..."

**Solution**:
- Removed generic "youtube" from UI filter list
- Kept specific "privacy-enhanced mode" filter for YouTube embed UI
- Added comment warning against overly broad filters

#### Fix 2: YouTube Link Detection
**Problem**: YouTube links in paragraphs not converted to embeds

**Solution**: Added automatic YouTube link detection in `_add_paragraph_block()`:
- Detects `youtube.com/watch?v=` and `youtu.be/` links
- Extracts video ID
- Creates `youtube_embed` blocks automatically
- Prevents duplicates using `youtube_urls` set
- Supports timestamp parameters (`&t=123`, `#timestamp`)

**Example**:
```html
<!-- Input -->
<p>Watch the video: <a href="https://youtu.be/ABC123">link</a></p>

<!-- Output -->
- youtube_embed block (with thumbnail)
- paragraph block (with text)
```

### Video Classification Fix
**File**: `src/patreon_scraper_v2.py`

**Problem**: Non-video files counted as videos (PDFs, images in post 98662540)

**Root Cause**: `_enrich_video_sources()` added ALL URLs from API without validation

**Solution**: Added extension filtering in `register()` function:
```python
video_extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv', '.flv', '.wmv')
if url_path.endswith(video_extensions):
    download_urls.add(url)
else:
    logger.debug(f"Skipping non-video URL: {url[:80]}...")
```

**Impact**:
- Accurate video counts in post headers
- PDFs and images no longer shown as videos
- Better user experience

## Testing & Migration

### To Apply Fixes:
```bash
cd ~/proyectos/astrologia/patreon
git pull origin claude/review-project-documentation-011CUvM1DgV35NYNs5xCfpGd

# Re-process affected creator (e.g., Skyscript)
python3 src/phase2_detail_extractor.py --creator skyscript

# Restart Flask
python3 web/viewer.py
```

### Affected Posts (Examples):
- **141803080** (Skyscript): Missing YouTube content, lost paragraphs
- **98662540** (Skyscript): Incorrect video count (2 shown, 0 actual)

## Technical Debt Resolved

1. **Deduplication vs. User Experience**: Balanced hash-based storage with user-friendly downloads
2. **Content Filtering**: Made filters more precise to avoid false positives
3. **Media Classification**: Proper validation of file types
4. **Documentation**: Added comprehensive docstrings and comments

## Breaking Changes

None. All changes are backward compatible.

## Future Considerations

1. Consider extracting original filenames for images/videos from Patreon metadata (currently from URL)
2. May need similar link detection for other platforms (Vimeo, SoundCloud, etc.)
3. Consider caching thumbnail lookups for YouTube videos
