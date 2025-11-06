# Recent Updates & New Structure

## 📂 New Project Structure

```
patreon/
├── src/                              ← Main source code
│   ├── phase1_url_collector.py      ← Collect post URLs
│   ├── phase2_detail_extractor.py   ← Extract post details  
│   ├── phase3_collections_scraper.py ← Scrape collections
│   ├── daily_incremental_scrape.py  ← NEW: Daily updates (fast)
│   ├── add_creator.py               ← NEW: Add creators
│   ├── reset_creator.py             ← NEW: Reset creator data
│   ├── fix_corrupted_json.py        ← NEW: Repair JSONs
│   └── ...
├── tools/                            ← Utility scripts
│   ├── test_single_post.py
│   ├── clean_vtt_files.py
│   └── ...
├── web/                              ← Web viewer
│   ├── viewer.py                    ← Flask app
│   └── templates/
└── docs/                             ← Documentation
```

## 🚀 Quick Start - Daily Workflow

### For Daily Updates (Recommended)
```bash
# Fast incremental update (only new posts)
python src/daily_incremental_scrape.py --all

# Process pending details
python src/phase2_detail_extractor.py --all --headless

# Update collections  
python src/phase3_collections_scraper.py --all --headless
```

### For New Creator Setup
```bash
# 1. Add creator
python src/add_creator.py

# 2. Full scrape (first time)
python src/phase1_url_collector.py --creator CREATOR_NAME
python src/phase2_detail_extractor.py --creator CREATOR_NAME --headless
python src/phase3_collections_scraper.py --creator CREATOR_NAME --headless
```

## ⚡ Performance Improvements

- **Daily Incremental Scraper**: 10-100x faster than full scrape
- **Smart stopping**: Stops at first known post
- **Bandwidth efficient**: Only checks recent posts

## 🔧 Tools Available

### Creator Management
- `src/add_creator.py` - Add new creators interactively
- `src/reset_creator.py` - Reset creator data (with backup)

### Diagnostics
- `src/diagnose_headonhistory.py` - Debug missing creators
- `src/debug_creators.py` - Check post distribution
- `src/fix_corrupted_json.py` - Repair corrupted JSON files

## 📖 Full Documentation

- **Main README**: [README.md](README.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Workflow**: [WORKFLOW.md](WORKFLOW.md)
