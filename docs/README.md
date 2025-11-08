# Documentation Index

Comprehensive documentation for the Patreon scraper project.

---

## 📚 Available Documentation

### Bug Fixes & Troubleshooting

**[BUGFIXES_PHASE2.md](BUGFIXES_PHASE2.md)**
- Critical bugs found during Phase 2 development
- **Bug #1:** Posts not inserting into PostgreSQL (missing source_id)
- **Bug #2:** "With audio" filter showing 0 posts
- Root cause analysis and solutions
- Diagnostic tools and testing procedures

### System Architecture

**[MEDIA_ARCHITECTURE.md](MEDIA_ARCHITECTURE.md)**
- Three-phase scraping architecture
- PostgreSQL schema for media storage
- Content blocks vs media arrays
- How filters work (template + Python)
- Deduplication system
- File structure and paths
- Viewer implementation details

### Configuration

**[SETTINGS_CONFIG.md](SETTINGS_CONFIG.md)**
- Complete guide to `config/settings.json`
- Image download settings (filtering, deduplication)
- Patreon video/audio configuration
- YouTube integration options
- Scraping parameters (retries, timeouts)
- Celery distributed processing
- Configuration examples (conservative, archival, development)
- Common mistakes and safe update process

---

## 🚀 Quick Start

### First Time Setup

1. **Read architecture overview:**
   ```bash
   cat docs/MEDIA_ARCHITECTURE.md
   ```

2. **Configure settings:**
   ```bash
   nano config/settings.json
   # See SETTINGS_CONFIG.md for options
   ```

3. **Run scraper:**
   ```bash
   python3 src/orchestrator.py --creator astrobymax
   ```

### Troubleshooting

1. **Filter not working?**
   - Read: `BUGFIXES_PHASE2.md` → Bug #2

2. **Posts not inserting?**
   - Read: `BUGFIXES_PHASE2.md` → Bug #1

3. **Media not downloading?**
   - Read: `SETTINGS_CONFIG.md` → Media Settings

---

## 📖 Documentation by Topic

### Understanding How Media Works

1. **Start here:** `MEDIA_ARCHITECTURE.md` → Overview
2. **Then read:** `MEDIA_ARCHITECTURE.md` → Media Storage in PostgreSQL
3. **Finally:** `MEDIA_ARCHITECTURE.md` → Media Filtering in Web Viewer

### Configuring Downloads

1. **Start here:** `SETTINGS_CONFIG.md` → Media Settings
2. **For images:** `SETTINGS_CONFIG.md` → Images → Image Filtering
3. **For videos:** `SETTINGS_CONFIG.md` → Patreon Videos
4. **For audio:** `SETTINGS_CONFIG.md` → Patreon Audio

### Debugging Issues

1. **Phase 2 errors:** `BUGFIXES_PHASE2.md`
2. **Filter issues:** `BUGFIXES_PHASE2.md` → Bug #2
3. **Database errors:** `BUGFIXES_PHASE2.md` → Bug #1
4. **Common issues:** `MEDIA_ARCHITECTURE.md` → Common Issues

---

## 🔧 Tools & Scripts

### Diagnostic Scripts

**`tools/diagnose_phase2_data.py`**
- Compares JSON vs PostgreSQL data
- Checks media counts
- Tests filter conditions
- Verifies downloaded files

```bash
python3 tools/diagnose_phase2_data.py
```

**`tools/validate_phase2_upsert.py`**
- Pre-commit validation
- Checks table structure
- Tests UPSERT SQL syntax
- Verifies constraints

```bash
python3 tools/validate_phase2_upsert.py
```

**`tools/check_audio_issue.py`**
- Quick audio filter diagnostic
- Shows how viewer counts audio

```bash
python3 tools/check_audio_issue.py
```

### Database Queries

**Check posts with audio:**
```sql
SELECT post_id, title, array_length(audio_local_paths, 1) as audio_count
FROM posts
WHERE creator_id = 'astrobymax'
  AND audio_local_paths IS NOT NULL
ORDER BY post_id;
```

**Check media downloads:**
```bash
# Audio files
ls -la data/media/audio/astrobymax/

# Image files
ls -la data/media/images/astrobymax/

# Video files
ls -la data/media/videos/astrobymax/
```

---

## 🐛 Known Issues

### Issue: "With audio" filter shows 0 posts

**Status:** ✅ FIXED (commit f49bde2)

**Solution:** Update `index.html` to use `audio_local_paths` instead of content_blocks

**Details:** See `BUGFIXES_PHASE2.md` → Bug #2

### Issue: Posts not inserting (source_id violation)

**Status:** ✅ FIXED (commit eacf7ea)

**Solution:** Added source_id resolution in Phase 2 UPSERT

**Details:** See `BUGFIXES_PHASE2.md` → Bug #1

---

## 📁 File Structure

```
docs/
├── README.md                    # This file (documentation index)
├── BUGFIXES_PHASE2.md          # Bug fixes and solutions
├── MEDIA_ARCHITECTURE.md       # System architecture
└── SETTINGS_CONFIG.md          # Configuration guide

config/
├── settings.json               # Media download configuration
└── creators.json               # Creator definitions

tools/
├── diagnose_phase2_data.py     # Diagnostic script
├── validate_phase2_upsert.py   # Pre-commit validation
└── check_audio_issue.py        # Audio filter diagnostic

src/
├── orchestrator.py             # Main entry point
├── phase1_posts_lister.py      # Phase 1: List posts
├── phase2_detail_extractor.py  # Phase 2: Extract details
└── phase3_media_downloader.py  # Phase 3: Download media

web/
├── viewer.py                   # Flask web viewer
└── templates/
    ├── index.html              # Post list view
    └── post.html               # Single post view

data/
├── processed/
│   ├── {creator}_posts_list.json     # Phase 1 output
│   └── {creator}_posts_detailed.json # Phase 2 output
└── media/
    ├── images/{creator}/       # Downloaded images
    ├── audio/{creator}/        # Downloaded audio
    └── videos/{creator}/       # Downloaded videos
```

---

## 🔄 Update Process

When updating documentation:

1. **Edit relevant file:**
   ```bash
   nano docs/MEDIA_ARCHITECTURE.md
   ```

2. **Update this index if needed:**
   ```bash
   nano docs/README.md
   ```

3. **Commit changes:**
   ```bash
   git add docs/
   git commit -m "DOCS: Update [topic] documentation"
   git push
   ```

---

## 📞 Getting Help

### For Bug Reports

1. **Check existing docs:**
   - `BUGFIXES_PHASE2.md` for known issues
   - `MEDIA_ARCHITECTURE.md` → Common Issues

2. **Run diagnostics:**
   ```bash
   python3 tools/diagnose_phase2_data.py
   ```

3. **Include in report:**
   - Error message
   - Diagnostic output
   - Steps to reproduce

### For Configuration Help

1. **Read:** `SETTINGS_CONFIG.md`
2. **Check examples:** `SETTINGS_CONFIG.md` → Configuration Examples
3. **Validate:** `python3 -m json.tool config/settings.json`

---

## 📝 Document Changelog

### 2025-11-08
- **Added:** `BUGFIXES_PHASE2.md` - Phase 2 bug documentation
- **Added:** `MEDIA_ARCHITECTURE.md` - System architecture guide
- **Added:** `SETTINGS_CONFIG.md` - Configuration reference
- **Added:** `README.md` - Documentation index (this file)

---

## 🏗️ Future Documentation

Planned documentation to add:

- [ ] **PHASE1_GUIDE.md** - Phase 1 post listing
- [ ] **PHASE3_GUIDE.md** - Phase 3 media downloading
- [ ] **SCHEMA_MIGRATION.md** - Database schema changes
- [ ] **DEPLOYMENT.md** - Production deployment guide
- [ ] **API_REFERENCE.md** - Internal API documentation
- [ ] **TESTING.md** - Testing procedures and test suite

---

## 📚 External References

### PostgreSQL Documentation
- [JSONB Type](https://www.postgresql.org/docs/current/datatype-json.html)
- [Array Types](https://www.postgresql.org/docs/current/arrays.html)
- [UPSERT (INSERT ON CONFLICT)](https://www.postgresql.org/docs/current/sql-insert.html)

### Python Libraries
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Flask](https://flask.palletsprojects.com/)
- [Selenium](https://selenium-python.readthedocs.io/)

### Tools
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

**Last Updated:** 2025-11-08
**Version:** 1.0
