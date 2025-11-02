# 🚀 Complete Workflow Guide - Patreon to Notion

**From Scraping to Notion - Step by Step**

---

## 📊 Complete Pipeline Overview

```
1. Authenticate → 2. Scrape Posts → 3. Download Media → 4. Generate Tags → 5. Upload to Notion
     (1 time)        (periodic)         (automatic)        (AI-powered)       (final step)
```

---

## 🎯 Step 1: Initial Setup (One Time Only)

### Activate Virtual Environment

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate
```

### Authenticate with Patreon

```bash
python src/main.py --auth-only
```

**What happens**:
1. Chrome browser opens
2. You manually log into Patreon
3. Press ENTER when logged in
4. Cookies are saved (valid ~1 month)

✅ **You only need to do this once a month!**

---

## 🎯 Step 2: Scrape Posts

### Option A: Quick Test (Recommended First Time)

```bash
# Scrape 5 posts from each creator (fast preview)
python src/main.py --scrape-all --limit 5
```

**Time**: ~2-3 minutes
**Output**: Basic metadata (titles, dates, preview text, preview images)

### Option B: Full Scrape (Production)

```bash
# Scrape ALL posts with FULL details (images, videos, audio URLs)
python src/main.py --scrape-all --full-details
```

**Time**: ~2-4 hours (depending on total posts)
**Output**: Complete data including all multimedia URLs

### Option C: Single Creator

```bash
# Just one creator with full details
python src/main.py --creator headonhistory --full-details
```

**Files Generated**:
```
data/raw/
├── headonhistory_posts.json
├── astrobymax_posts.json
└── horoiproject_posts.json
```

---

## 🎯 Step 3: Download Multimedia

After scraping, download all images, videos, and audio files:

```bash
python src/media_downloader.py --all
```

**What it downloads**:
- All images → `data/media/images/{creator_id}/`
- All videos → `data/media/videos/{creator_id}/`
- All audio → `data/media/audio/{creator_id}/`

**Features**:
- Skips already downloaded files
- Shows progress for each file
- Generates download manifest
- Displays statistics at the end

**Time**: Depends on total media size (could be several GB)

---

## 🎯 Step 4: Generate Tags with AI

### Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy it

### Set API Key

```bash
# Option 1: Export as environment variable
export GEMINI_API_KEY="your-api-key-here"

# Option 2: Add to your .bashrc for permanent use
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### Generate Tags

```bash
# Process ALL scraped posts and generate tags
python src/tag_generator.py --all
```

**What it does**:
1. Reads each post's title and content
2. Uses Gemini AI to analyze and generate relevant tags
3. Saves processed posts to `data/processed/`
4. Generates tag frequency statistics
5. Shows top 20 most common tags

**Example output**:
```json
{
  "creator_id": "headonhistory",
  "post_id": "123456",
  "title": "The Fall of Rome",
  "content": "...",
  "tags": [
    "ancient-history",
    "rome",
    "empire",
    "military-strategy",
    "political-decline",
    "analysis"
  ],
  "tags_generated_at": "2025-11-01T10:30:00"
}
```

**Files Generated**:
```
data/processed/
├── headonhistory_posts.json
├── headonhistory_posts_tag_summary.json
├── astrobymax_posts.json
├── astrobymax_posts_tag_summary.json
├── horoiproject_posts.json
└── horoiproject_posts_tag_summary.json
```

**Time**: ~1-2 minutes per post (due to AI processing)
**Cost**: Free tier allows 60 requests per minute

---

## 🎯 Step 5: Upload to Notion (Coming Soon)

```bash
# This will be implemented next
python src/notion_integrator.py --upload-all
```

**What it will do**:
1. Create 3 Notion databases:
   - **Posts** - All articles with content, media, tags
   - **Tags** - All tags with descriptions and post counts
   - **Creators** - Creator profiles with statistics
2. Upload all posts with relationships
3. Upload all media files to Notion
4. Create tag relationships
5. Generate statistics pages

---

## 📊 Complete Example Workflow

Here's a real example from start to finish:

```bash
# ========================================
# DAY 1: Initial Setup
# ========================================

cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

# Authenticate once
python src/main.py --auth-only
# → Login manually in browser
# → Press ENTER
# ✅ Cookies saved


# ========================================
# DAY 1: Test Scrape
# ========================================

# Quick test with 5 posts per creator
python src/main.py --scrape-all --limit 5
# ⏱️  Takes 2-3 minutes
# ✅ 15 posts scraped (5 × 3 creators)

# Check results
cat data/raw/headonhistory_posts.json | jq '.[0]'


# ========================================
# DAY 1: Full Production Scrape
# ========================================

# Scrape ALL posts with full details
# (Run this overnight or in background)
nohup python src/main.py --scrape-all --full-details > scrape.log 2>&1 &

# Monitor progress
tail -f scrape.log

# ⏱️  Takes 2-4 hours
# ✅ Hundreds of posts with complete data


# ========================================
# DAY 2: Download Media
# ========================================

# Download all images, videos, audio
python src/media_downloader.py --all

# ⏱️  Depends on total size (could be hours for GB of data)
# ✅ All media organized in data/media/


# ========================================
# DAY 2: Generate Tags
# ========================================

# Set up Gemini API key (one time)
export GEMINI_API_KEY="your-key-here"

# Generate tags for all posts
python src/tag_generator.py --all

# ⏱️  ~1-2 minutes per post
# ✅ Tags generated and saved to data/processed/

# View tag statistics
cat data/processed/headonhistory_posts_tag_summary.json | jq '.tag_frequency'


# ========================================
# DAY 3: Upload to Notion (coming soon)
# ========================================

python src/notion_integrator.py --upload-all

# ✅ Everything organized in Notion!
```

---

## 🔄 Regular Updates (Monthly)

Once set up, you can update your Notion with new content:

```bash
cd /home/javif/proyectos/astrologia/patreon
source venv/bin/activate

# 1. Re-authenticate if cookies expired (monthly)
python src/main.py --auth-only

# 2. Scrape new posts only (incremental scraping - coming soon)
python src/main.py --scrape-all --full-details --since-last-run

# 3. Download new media
python src/media_downloader.py --all

# 4. Generate tags for new posts
python src/tag_generator.py --all

# 5. Upload new posts to Notion
python src/notion_integrator.py --upload-new
```

---

## 📁 Complete File Structure After All Steps

```
patreon/
├── src/
│   ├── patreon_auth_selenium.py   ✅ Done
│   ├── patreon_scraper.py         ✅ Done
│   ├── media_downloader.py        ✅ Done
│   ├── tag_generator.py           ✅ Done
│   ├── notion_integrator.py       ⏳ Next
│   └── main.py                    ✅ Done
├── data/
│   ├── raw/                       ✅ Scraped JSONs
│   ├── processed/                 ✅ Tagged JSONs
│   └── media/
│       ├── images/                ✅ Downloaded images
│       ├── videos/                ✅ Downloaded videos
│       └── audio/                 ✅ Downloaded audio
├── config/
│   ├── credentials.json           ✅ Credentials
│   └── patreon_cookies.json       ✅ Session cookies
├── logs/
│   ├── main.log
│   ├── scraper.log
│   ├── media_downloader.log
│   └── tag_generator.log
└── venv/                          ✅ Virtual environment
```

---

## ⏱️ Time Estimates

| Step | Quick Mode | Full Mode |
|------|-----------|-----------|
| 1. Authentication | 1 minute | 1 minute |
| 2. Scraping (3 creators) | 2-3 min (5 posts each) | 2-4 hours (all posts) |
| 3. Media Download | 10-30 min | 1-4 hours (depends on size) |
| 4. Tag Generation | 5-10 min | 30-60 min |
| 5. Notion Upload | TBD | TBD |

**Total for Full Pipeline**: ~4-8 hours (mostly automated)

---

## 💾 Storage Requirements

Estimate for 3 creators with ~500 posts each:

- **JSON data**: ~50-100 MB
- **Images**: ~2-5 GB
- **Videos**: ~10-20 GB (if many videos)
- **Audio**: ~1-3 GB (if many audio posts)

**Total**: ~15-30 GB (varies greatly by content type)

---

## 🎓 Tips & Best Practices

### For First Time Users

1. **Start small**: Use `--limit 5` to test everything first
2. **Check results**: Look at the generated JSONs before full scrape
3. **Monitor logs**: Keep `tail -f logs/*.log` open in another terminal
4. **Backup data**: Copy `data/` directory before major operations

### For Production Use

1. **Use nohup for long scrapes**: Don't let terminal disconnections stop you
2. **Schedule regular updates**: Use cron for monthly scraping
3. **Monitor disk space**: Media files can grow large
4. **Rate limit friendly**: Built-in delays prevent Patreon blocking

### Troubleshooting

**Cookies expired?**
```bash
python src/main.py --auth-only
```

**Gemini API rate limit?**
```bash
# Edit tag_generator.py and increase sleep time
time.sleep(2)  # Instead of 1 second
```

**Download interrupted?**
```bash
# Just re-run, it will skip existing files
python src/media_downloader.py --all
```

**Want to re-process tags?**
```bash
# Delete processed files and re-run
rm data/processed/*
python src/tag_generator.py --all
```

---

## 🎯 What's Next?

The final piece of the puzzle is the **Notion Integration**:

1. Create Notion databases (Posts, Tags, Creators)
2. Upload all posts with rich content
3. Upload media files
4. Create relationships between databases
5. Generate summary/statistics pages

**Coming soon**: `src/notion_integrator.py`

---

## ✅ Current Status

- ✅ **Authentication**: Selenium-based, manual mode, cookie persistence
- ✅ **Scraping**: Infinite scroll, full details, robust selectors
- ✅ **Media Download**: Images, videos, audio, organized storage
- ✅ **Tag Generation**: Gemini AI, smart prompts, frequency stats
- ⏳ **Notion Integration**: Next step!

---

**¡El sistema está casi completo! Solo falta la integración con Notion.** 🚀
