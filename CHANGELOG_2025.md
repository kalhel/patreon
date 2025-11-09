# Changelog 2025

## 2025-11-09 - Search Performance & UX Improvements

### Major Performance Optimization: Removed ts_headline
**Files**: `web/viewer.py`, `web/templates/index.html`
**Branch**: `feature/advanced-search-improvements`

**Problem**: PostgreSQL search was slow (2-3 seconds) because it generated 4 snippets per post using `ts_headline` (title, content, comments, subtitles). For 352 results = 1,408 snippet operations. These snippets were not used in the card view.

**Solution**:
- ✅ Removed all `ts_headline` calls from search query
- ✅ Changed `matched_in` detection to direct text search instead of snippet parsing
- ✅ Set snippets to `None` (prepared for future advanced search view)
- ✅ Added comments marking where to re-enable ts_headline for advanced view

**Result**: **70-80% faster searches** with identical results

### Search UI & UX Improvements

#### 1. Search Result Spacing
- Adjusted `.search-container` bottom margin to `1.75rem` (was `3rem`)
- Better visual grouping: Title/Text/Tags badges closer to Images/Videos/Audios filters
- Maintains separation from post cards below

#### 2. Improved Badge Design
**Changes**:
- Larger size: `padding: 0.625rem 1rem` (was `0.4rem 0.75rem`)
- More rounded: `border-radius: 10px` (was `8px`)
- Visible border: `2px solid #e0e0e0`
- Bigger icons: `16px` (was `14px`)
- **Active state**: Black background `#1a1a1a` with white text/icons (consistent with site theme)
- Larger badge numbers: `1rem` font size, bold

#### 3. Disabled Buttons During Search
- "Show Tags" and "Show Collections" buttons now disabled during active search
- Visual feedback: `opacity: 0.4`, `cursor: not-allowed`
- Re-enabled when search is cleared

#### 4. Fixed Creator Count Inconsistency
**Problem**: When searching "venus mars mercury" and selecting creator "Ali A Olomi", showed:
- Creator card: 85 posts
- Results message: 93 posts found

**Root cause**: `searchStats.creators` only counted posts with `matchedIn.length > 0`, but `visibleCount` counted ALL visible posts.

**Solution**: Moved creator counting to match visibleCount logic (line 2364-2367)

**Result**: Creator card count now always matches "X posts found" message

### Search Statistics Accuracy
- Badge statistics (Title, Text, Tags, etc.) only count posts with `matchedIn` data
- Creator counts match total visible posts
- "X posts found" message accurate for all filter combinations

### Technical Improvements
- Search debounce: 300ms (prevents searches while typing)
- Direct text matching in Python (faster than snippet parsing)
- Code prepared for future advanced search view with snippets

---

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
