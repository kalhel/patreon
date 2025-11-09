#!/usr/bin/env python3
"""
Web Viewer - Local web app to preview scraped Patreon posts
Displays posts with formatting similar to Patreon before uploading to Notion

DUAL MODE: Reads from PostgreSQL (if flag enabled) or JSON (fallback)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_compress import Compress
from flask_caching import Cache
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import PostgreSQL tracker for live status
try:
    from postgres_tracker import PostgresTracker
    POSTGRES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  PostgreSQL tracker not available: {e}")
    POSTGRES_AVAILABLE = False

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Configure caching
cache_config = {
    'CACHE_TYPE': os.getenv('CACHE_TYPE', 'SimpleCache'),  # SimpleCache or RedisCache
    'CACHE_DEFAULT_TIMEOUT': int(os.getenv('CACHE_TIMEOUT', 900)),  # 15 minutes default (increased from 5)
}

# If using Redis cache
if cache_config['CACHE_TYPE'] == 'RedisCache':
    cache_config.update({
        'CACHE_REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
        'CACHE_REDIS_PORT': int(os.getenv('REDIS_PORT', 6379)),
        'CACHE_REDIS_DB': int(os.getenv('REDIS_DB', 0)),
        'CACHE_REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    })

app.config.from_mapping(cache_config)
cache = Cache(app)

# Enable gzip compression
Compress(app)

# Custom Jinja2 filter for basic markdown to HTML
import re

@app.template_filter('markdown')
def markdown_filter(text):
    """Convert basic markdown to HTML (preserves HTML tags like <u>)"""
    if not text:
        return ''

    # Links FIRST: [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)

    # Auto-link bare URLs: http://example.com or https://example.com
    # Negative lookbehind to avoid double-linking already processed URLs
    text = re.sub(
        r'(?<!\()(?<!href=")(https?://[^\s<>"]+)',
        r'<a href="\1" target="_blank">\1</a>',
        text
    )

    # Bold: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Italic: *text* -> <em>text</em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # HTML tags like <u>text</u> are already valid, leave as is

    # Line breaks: \n -> <br>
    text = text.replace('\n', '<br>')

    return text

# Data directories - try both raw and processed
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
MEDIA_ROOT = Path(__file__).parent.parent / "data" / "media"

# Display names for creators
CREATOR_DISPLAY_NAMES = {
    'headonhistory': 'Ali A Olomi',
    'horoiproject': 'HOROI Project',
    'astrobymax': 'AstroByMax'
}

# Local avatar paths for creators (dynamically loaded from creators.json)
CREATOR_AVATARS = {}


def load_creators_config():
    """Load creators configuration from config file"""
    config_dir = Path(__file__).parent.parent / "config"
    creators_file = config_dir / "creators.json"

    if creators_file.exists():
        try:
            with open(creators_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                creators_list = data.get('creators', [])

                # Build CREATOR_AVATARS dynamically from creators.json
                global CREATOR_AVATARS
                CREATOR_AVATARS = {}
                for creator in creators_list:
                    creator_id = creator.get('creator_id')
                    avatar = creator.get('avatar')
                    if creator_id and avatar:
                        CREATOR_AVATARS[creator_id] = avatar

                return creators_list
        except Exception as e:
            print(f"Error loading creators config: {e}")
            pass
    return []


def format_date_eu(date_str):
    """Convert various date strings to DD/MM/YY format"""
    if not date_str:
        return 'N/A'
    text = str(date_str).strip()

    if 'T' in text:
        text = text.split('T')[0]

    # Remove common separators/phrases before parsing
    text = text.replace(' at ', ' ')

    date_formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
        '%B %d, %Y',
        '%b %d, %Y',
        '%B %d %Y',
        '%b %d %Y',
        '%B %d, %Y %I:%M %p',
        '%b %d, %Y %I:%M %p'
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime('%d/%m/%y')
        except ValueError:
            continue

    # Attempt to parse numeric day/month/year even if separator differs
    if '-' in text or '/' in text:
        separator = '-' if '-' in text else '/'
        parts = text.split(separator)
        if len(parts) == 3 and all(len(part) >= 1 for part in parts):
            if len(parts[0]) == 4:
                return f"{parts[2][:2]}/{parts[1][:2]}/{parts[0][-2:]}"
            if len(parts[2]) == 4:
                return f"{parts[0][:2]}/{parts[1][:2]}/{parts[2][-2:]}"

    return text


def get_creator_display_name(creator_id):
    """Get display name for creator"""
    return CREATOR_DISPLAY_NAMES.get(creator_id, creator_id)


def filter_actual_videos(videos_list):
    """
    Filter video URLs to only include actual video file extensions.
    Removes image URLs (.jpg, .png, etc.) that may have been incorrectly stored as videos.
    Also excludes Mux thumbnail URLs (use /medium.mp4, /low.mp4, /high.mp4).
    """
    if not videos_list:
        return []

    video_extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.m4v', '.mkv', '.m3u8', '.ts')
    actual_videos = []
    for v in videos_list:
        # Check if it has video extension
        if any(v.lower().split('?')[0].endswith(ext) for ext in video_extensions):
            # Exclude Mux thumbnails (paths like /medium.mp4, /low.mp4, /high.mp4)
            # Real Mux videos use .m3u8 or /video.mp4
            if 'stream.mux.com' in v.lower() and ('/medium.mp4' in v.lower() or '/low.mp4' in v.lower() or '/high.mp4' in v.lower()):
                continue
            actual_videos.append(v)
    return actual_videos


# Register Jinja filters
app.jinja_env.filters['date_eu'] = format_date_eu
app.jinja_env.filters['creator_name'] = get_creator_display_name
app.jinja_env.filters['filter_videos'] = filter_actual_videos


# ============================================================================
# PostgreSQL Integration (Dual Mode)
# ============================================================================

def use_postgresql() -> bool:
    """Check if PostgreSQL mode is enabled via flag file"""
    flag_path = Path(__file__).parent.parent / "config" / "use_postgresql.flag"
    return flag_path.exists()


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables"""
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env file")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def search_posts_postgresql(query, limit=50, creator_filter=None):
    """
    Search posts using PostgreSQL Full-Text Search (FTS)

    Args:
        query: Search query string
        limit: Maximum number of results
        creator_filter: Optional creator_id to filter by

    Returns:
        List of search results with scores, matching SQLite FTS5 format
    """
    try:
        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Build tsquery (PostgreSQL full-text query)
            # Convert space-separated words to AND query (more precise search)
            search_terms = query.strip().split()

            # Create AND query with prefix matching (term:*)
            tsquery_parts = [f"{term}:*" for term in search_terms if term]
            tsquery = ' & '.join(tsquery_parts)  # AND operator

            # Build SQL with optional creator filter
            creator_condition = "AND p.creator_id = :creator_id" if creator_filter else ""

            sql = text(f"""
                SELECT
                    p.post_id,
                    p.creator_id,
                    p.creator_name,
                    p.title,
                    p.published_at,
                    p.like_count,
                    p.comment_count,
                    p.images,
                    p.videos,
                    p.audios,
                    p.patreon_tags,
                    p.full_content,
                    p.comments_text,
                    p.subtitles_text,
                    ts_rank(p.search_vector, to_tsquery('english', :tsquery)) as rank,
                    ts_headline('english', COALESCE(p.title, ''), to_tsquery('english', :tsquery),
                               'StartSel=<mark>, StopSel=</mark>, MaxWords=20') as title_snippet,
                    ts_headline('english', COALESCE(p.full_content, ''), to_tsquery('english', :tsquery),
                               'StartSel=<mark>, StopSel=</mark>, MaxWords=30') as content_snippet,
                    ts_headline('english', COALESCE(p.comments_text, ''), to_tsquery('english', :tsquery),
                               'StartSel=<mark>, StopSel=</mark>, MaxWords=30') as comments_snippet,
                    ts_headline('english', COALESCE(p.subtitles_text, ''), to_tsquery('english', :tsquery),
                               'StartSel=<mark>, StopSel=</mark>, MaxWords=30') as subtitles_snippet
                FROM posts p
                WHERE p.search_vector @@ to_tsquery('english', :tsquery)
                    AND p.deleted_at IS NULL
                    {creator_condition}
                ORDER BY rank DESC
                LIMIT :limit
            """)

            params = {
                'tsquery': tsquery,
                'limit': limit
            }

            if creator_filter:
                params['creator_id'] = creator_filter

            result = conn.execute(sql, params)

            results = []
            for row in result:
                # Determine which fields matched
                matched_in = []

                # Check snippets for highlights
                title_snippet = row.title_snippet or ''
                content_snippet = row.content_snippet or ''
                comments_snippet = row.comments_snippet or ''
                subtitles_snippet = row.subtitles_snippet or ''

                if '<mark>' in title_snippet:
                    matched_in.append('title')
                if '<mark>' in content_snippet:
                    matched_in.append('content')
                if '<mark>' in comments_snippet:
                    matched_in.append('comments')
                if '<mark>' in subtitles_snippet:
                    matched_in.append('subtitles')

                # Check tags (simple string matching for now)
                tags_list = row.patreon_tags or []
                tags_text = ' '.join(tags_list).lower()
                if any(term.lower() in tags_text for term in search_terms):
                    matched_in.append('tags')

                # Format result to match SQLite FTS5 structure
                result_item = {
                    'post_id': row.post_id,
                    'creator_id': row.creator_id,
                    'creator_name': row.creator_name,
                    'title': row.title,
                    'rank': float(row.rank),  # PostgreSQL ts_rank (higher = better)
                    'matched_in': matched_in,
                    'snippets': {
                        'title': title_snippet,
                        'content': content_snippet,
                        'tags': None,  # TODO: Generate tag snippet
                        'comments': comments_snippet if comments_snippet else None,
                        'subtitles': subtitles_snippet if subtitles_snippet else None
                    },
                    'published_date': row.published_at.strftime('%d %b %Y') if row.published_at else None,
                    'has_images': bool(row.images and len(row.images) > 0),
                    'has_videos': bool(row.videos and len(row.videos) > 0),
                    'has_audio': bool(row.audios and len(row.audios) > 0),
                    'counts': {
                        'images': len(row.images) if row.images else 0,
                        'videos': len(row.videos) if row.videos else 0,
                        'audio': len(row.audios) if row.audios else 0,
                        'comments': row.comment_count or 0,
                        'likes': row.like_count or 0
                    }
                }

                results.append(result_item)

            return results

    except Exception as e:
        print(f"⚠️  PostgreSQL search failed: {e}")
        raise


@cache.memoize(timeout=900)  # Cache for 15 minutes (optimized)
def load_posts_from_postgres():
    """Load all posts from PostgreSQL database with collections"""
    try:
        print("🐘 Loading posts from PostgreSQL...")
        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Get all posts (not deleted)
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
                    created_at,
                    updated_at,
                    creator_name,
                    creator_avatar,
                    like_count,
                    comment_count,
                    images,
                    videos,
                    audios,
                    attachments,
                    image_local_paths,
                    video_local_paths,
                    audio_local_paths,
                    attachment_local_paths,
                    video_streams,
                    video_subtitles,
                    patreon_tags,
                    status
                FROM posts
                WHERE deleted_at IS NULL
                ORDER BY post_id DESC
            """)

            result = conn.execute(query)
            rows = result.fetchall()

            posts = []
            for row in rows:
                # Extract video_subtitles_relative from video_subtitles JSONB
                video_subtitles = row[23] if row[23] else []
                video_subtitles_relative = []
                if isinstance(video_subtitles, list):
                    # If video_subtitles is a list of objects with 'path' or 'relative_path'
                    for subtitle in video_subtitles:
                        if isinstance(subtitle, dict):
                            if 'relative_path' in subtitle:
                                video_subtitles_relative.append(subtitle['relative_path'])
                            elif 'path' in subtitle:
                                # Extract relative path from full path
                                path = subtitle['path']
                                if 'media/' in path:
                                    video_subtitles_relative.append(path.split('media/')[-1])

                # Load post_metadata (row[6])
                post_metadata = row[6] if row[6] else {}

                # Extract published_date from metadata (the real published date from HTML)
                published_date = post_metadata.get('published_date') if post_metadata else None

                post = {
                    'post_id': row[0],
                    'creator_id': row[1],
                    'post_url': row[2],
                    'title': row[3],
                    'full_content': row[4],
                    'content_blocks': row[5],
                    'post_metadata': post_metadata,  # Now loaded from PostgreSQL
                    'published_date': published_date,  # Real date from HTML (e.g., "27 Feb 2024")
                    'published_at': row[7].isoformat() if row[7] else None,
                    'created_at': row[8].isoformat() if row[8] else None,
                    'updated_at': row[9].isoformat() if row[9] else None,
                    'creator_name': row[10],
                    'creator_avatar': row[11],
                    'like_count': row[12],
                    'likes_count': row[12],  # Alias for compatibility
                    'comment_count': row[13],
                    'comments_count': row[13],  # Alias for compatibility
                    'images': row[14] if row[14] else [],
                    'videos': row[15] if row[15] else [],
                    'audios': row[16] if row[16] else [],
                    'attachments': row[17] if row[17] else [],
                    'image_local_paths': row[18] if row[18] else [],
                    'video_local_paths': row[19] if row[19] else [],
                    'audio_local_paths': row[20] if row[20] else [],
                    'attachment_local_paths': row[21] if row[21] else [],
                    'video_streams': row[22] if row[22] else [],
                    'video_subtitles': video_subtitles,
                    'video_subtitles_relative': video_subtitles_relative,  # Extracted from JSONB
                    'patreon_tags': row[24] if row[24] else [],
                    'status': row[25] if row[25] else {},
                    'collections': []  # Will be populated below
                }
                posts.append(post)

            # Now load collections for all posts
            collections_query = text("""
                SELECT
                    pc.post_id,
                    pc.collection_id,
                    c.title as collection_name,
                    c.collection_url,
                    pc.order_in_collection,
                    c.collection_image,
                    c.collection_image_local
                FROM post_collections pc
                JOIN collections c ON pc.collection_id = c.collection_id
                WHERE c.deleted_at IS NULL
                ORDER BY pc.post_id, pc.order_in_collection
            """)

            coll_result = conn.execute(collections_query)
            coll_rows = coll_result.fetchall()

            # Build collections map: post_id -> [collections]
            collections_by_post = {}
            for coll_row in coll_rows:
                post_id = coll_row[0]
                collection_data = {
                    'collection_id': coll_row[1],
                    'collection_name': coll_row[2],
                    'collection_url': coll_row[3],
                    'order': coll_row[4],
                    'collection_image': coll_row[5],
                    'collection_image_local': coll_row[6]
                }

                if post_id not in collections_by_post:
                    collections_by_post[post_id] = []
                collections_by_post[post_id].append(collection_data)

            # Assign collections to posts
            for post in posts:
                post_id = post['post_id']
                if post_id in collections_by_post:
                    post['collections'] = collections_by_post[post_id]

            print(f"✅ Loaded {len(posts)} posts from PostgreSQL")
            print(f"✅ Loaded collections for {len(collections_by_post)} posts")
            return posts

    except Exception as e:
        print(f"❌ Error loading from PostgreSQL: {e}")
        import traceback
        print(traceback.format_exc())
        print(f"   Falling back to JSON...")
        return None


@cache.memoize(timeout=900)  # Cache for 15 minutes (optimized)
def load_posts_from_json():
    """Load all posts from JSON files (raw and processed) - ORIGINAL METHOD"""
    all_posts = []

    # Try raw directory first
    if RAW_DATA_DIR.exists():
        for json_file in RAW_DATA_DIR.glob("*_posts.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    print(f"DEBUG: Loaded {len(posts)} posts from {json_file.name}")
                    if posts:
                        sample_creator = posts[0].get('creator_id', 'unknown')
                        print(f"       Sample creator_id: {sample_creator}")
                    all_posts.extend(posts)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
    else:
        print(f"DEBUG: RAW_DATA_DIR does not exist: {RAW_DATA_DIR}")

    # Then try processed directory
    if PROCESSED_DATA_DIR.exists():
        for json_file in PROCESSED_DATA_DIR.glob("*_posts_detailed.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    print(f"DEBUG: Loaded {len(posts)} posts from {json_file.name}")
                    if posts:
                        sample_creator = posts[0].get('creator_id', 'unknown')
                        print(f"       Sample creator_id: {sample_creator}")
                    all_posts.extend(posts)
            except Exception as e:
                print(f"❌ ERROR loading {json_file.name}: {e}")
                print(f"   This file is corrupted and needs to be fixed!")
                print(f"   Run: python fix_corrupted_json.py {json_file}")
    else:
        print(f"DEBUG: PROCESSED_DATA_DIR does not exist: {PROCESSED_DATA_DIR}")

    print(f"DEBUG: Total posts loaded: {len(all_posts)}")

    # Sort by post_id (newest first)
    all_posts.sort(key=lambda x: x.get('post_id', ''), reverse=True)

    return all_posts


def load_all_posts():
    """
    Load all posts using dual mode:
    - If PostgreSQL flag exists: load from PostgreSQL
    - Otherwise: load from JSON files (fallback)
    """
    # DUAL MODE: Check if PostgreSQL is enabled
    if use_postgresql():
        print("🐘 PostgreSQL mode enabled - loading from database...")
        posts = load_posts_from_postgres()

        # If PostgreSQL fails, fallback to JSON
        if posts is None:
            print("⚠️  PostgreSQL failed, falling back to JSON...")
            posts = load_posts_from_json()
        else:
            print(f"✅ Loaded {len(posts)} posts from PostgreSQL")

        return posts
    else:
        print("📝 PostgreSQL mode disabled - loading from JSON files...")
        return load_posts_from_json()


@app.route('/')
def index():
    """Homepage showing all posts"""
    posts = load_all_posts()

    # Ensure creators config is loaded (populates CREATOR_AVATARS)
    if not CREATOR_AVATARS:
        load_creators_config()

    def ensure_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def filter_by_extension(values, extensions):
        if not values:
            return []
        cleaned = []
        for entry in ensure_list(values):
            if not entry:
                continue
            entry_str = str(entry).replace('\\', '/')
            if not extensions or any(entry_str.lower().endswith(ext) for ext in extensions):
                cleaned.append(entry_str)
        return cleaned

    # Process each post to filter video and audio paths and set display names
    for post in posts:
        local_video_paths = filter_by_extension(post.get('video_local_paths'), {'.mp4', '.m4v', '.mov', '.webm', '.mkv'})
        local_audio_paths = filter_by_extension(post.get('audio_local_paths'), {'.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus'})

        # Sort videos according to content_blocks order (Vimeo before YouTube, etc.)
        content_blocks = post.get('content_blocks', [])
        if content_blocks and local_video_paths:
            # Get video blocks in order (sorted by order field)
            video_blocks = sorted(
                [b for b in content_blocks if b.get('type') in ['video', 'youtube_embed', 'vimeo_embed']],
                key=lambda b: b.get('order', 999)
            )

            if len(video_blocks) > 1 and len(local_video_paths) > 1:
                # Create a mapping of video URL patterns to local paths
                sorted_videos = []
                for block in video_blocks:
                    block_url = block.get('url', '')
                    # Match local path to block URL (by video ID or filename pattern)
                    for local_path in local_video_paths:
                        if local_path not in sorted_videos:
                            # Check if this path matches the current block
                            # Vimeo: contains _vm, YouTube: contains _yt
                            if 'vimeo' in block_url.lower() and '_vm' in local_path:
                                sorted_videos.append(local_path)
                                break
                            elif 'youtube' in block_url.lower() and '_yt' in local_path:
                                sorted_videos.append(local_path)
                                break

                # Add any remaining videos that weren't matched
                for path in local_video_paths:
                    if path not in sorted_videos:
                        sorted_videos.append(path)

                local_video_paths = sorted_videos

        post['video_local_paths'] = local_video_paths
        post['audio_local_paths'] = local_audio_paths

        # Set display name using same logic as view_post
        metadata = post.get('post_metadata') or {}
        creator_id = post.get('creator_id', 'unknown')
        creator_display_name = metadata.get('creator_name') or get_creator_display_name(creator_id)
        if not creator_display_name:
            creator_display_name = creator_id or "Unknown Creator"
        post['display_creator_name'] = creator_display_name

    # Group by creator and build consistent avatar mapping
    creators = {}
    creator_avatars = {}
    for post in posts:
        creator_id = post.get('creator_id', 'unknown')
        if creator_id not in creators:
            creators[creator_id] = []
        creators[creator_id].append(post)

        # Build avatar mapping ONLY from CREATOR_AVATARS (loaded from creators.json)
        # This is the single source of truth - managed from /settings page
        if creator_id not in creator_avatars and creator_id in CREATOR_AVATARS:
            creator_avatars[creator_id] = f"/static/{CREATOR_AVATARS[creator_id]}"

    # DEBUG: Print creator post counts and avatars
    print("\n=== DEBUG: Creator Post Counts ===")
    for creator_id, creator_posts in creators.items():
        avatar = creator_avatars.get(creator_id, 'NO AVATAR')
        print(f"{creator_id}: {len(creator_posts)} posts | Avatar: {avatar}")
    print("===================================\n")

    # Load creator colors from config
    creators_config = load_creators_config()
    creator_colors = {c['creator_id']: c.get('preview_color', '#4db8a0') for c in creators_config}

    return render_template('index.html',
                          creators=creators,
                          creator_avatars=creator_avatars,
                          creator_colors=creator_colors,
                          total_posts=len(posts))


@app.route('/post/<post_id>')
def view_post(post_id):
    """View single post with full content"""
    posts = load_all_posts()

    # Find the post
    post = None
    for p in posts:
        if p.get('post_id') == post_id:
            post = p
            break

    if not post:
        return f"Post {post_id} not found", 404

    # Get referrer info (for "back to collection" button)
    from_collection_id = request.args.get('from_collection')
    from_creator_id = post.get('creator_id')

    metadata = post.get('post_metadata') or {}
    creator_id = post.get('creator_id', 'unknown')
    creator_display_name = metadata.get('creator_name') or get_creator_display_name(creator_id)
    if not creator_display_name:
        creator_display_name = creator_id or "Unknown Creator"

    # Get creator avatar ONLY from CREATOR_AVATARS (single source of truth)
    # Same as index page - no fallback to metadata['creator_avatar'] (inconsistent)
    creator_avatar = None
    if not CREATOR_AVATARS:
        load_creators_config()

    if creator_id in CREATOR_AVATARS:
        creator_avatar = f"/static/{CREATOR_AVATARS[creator_id]}"
    # NOTE: Removed fallback to metadata['creator_avatar'] - too inconsistent

    likes_count = metadata.get('likes_count') or post.get('like_count') or 0

    content_blocks = post.get('content_blocks') or []

    def count_blocks(block_type):
        return sum(1 for block in content_blocks if block.get('type') == block_type)

    # Priority: Use downloaded media paths first (most reliable), then URLs, then content_blocks
    # This is because *_local_paths represent actual downloaded files
    image_local = post.get('image_local_paths') or []
    audio_local = post.get('audio_local_paths') or []
    video_local = post.get('video_local_paths') or []
    attachment_local = post.get('attachment_local_paths') or []

    # Sort videos according to content_blocks order (Vimeo before YouTube, etc.)
    if content_blocks and video_local and len(video_local) > 1:
        # Get video blocks in order (sorted by order field)
        video_blocks = sorted(
            [b for b in content_blocks if b.get('type') in ['video', 'youtube_embed', 'vimeo_embed']],
            key=lambda b: b.get('order', 999)
        )

        if len(video_blocks) > 1:
            sorted_videos = []
            for block in video_blocks:
                block_url = block.get('url', '')
                # Match local path to block URL
                for local_path in video_local:
                    if local_path not in sorted_videos:
                        # Vimeo: contains _vm, YouTube: contains _yt
                        if 'vimeo' in block_url.lower() and '_vm' in local_path:
                            sorted_videos.append(local_path)
                            break
                        elif 'youtube' in block_url.lower() and '_yt' in local_path:
                            sorted_videos.append(local_path)
                            break

            # Add any remaining videos
            for path in video_local:
                if path not in sorted_videos:
                    sorted_videos.append(path)

            video_local = sorted_videos

        # Update post with sorted videos
        post['video_local_paths'] = video_local

    # Count actual downloaded media
    image_count = len(image_local) if image_local else len(post.get('images') or [])
    audio_count = len(audio_local) if audio_local else len(post.get('audios') or [])

    # Filter videos field to only count actual video files (not images or thumbnails)
    # Old data may have image URLs in the videos field
    # Also filter out Mux thumbnail URLs (use /medium.mp4, /low.mp4, /high.mp4)
    video_extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.m4v', '.mkv', '.m3u8', '.ts')
    videos_raw = post.get('videos') or []
    actual_videos = []
    for v in videos_raw:
        # Check if it has video extension
        if any(v.lower().split('?')[0].endswith(ext) for ext in video_extensions):
            # Exclude Mux thumbnails (paths like /medium.mp4, /low.mp4, /high.mp4)
            # Real Mux videos use .m3u8 or /video.mp4
            if 'stream.mux.com' in v.lower() and ('/medium.mp4' in v.lower() or '/low.mp4' in v.lower() or '/high.mp4' in v.lower()):
                continue
            actual_videos.append(v)
    video_count = len(video_local) if video_local else len(actual_videos)

    attachment_count = len(attachment_local) if attachment_local else len(post.get('attachments') or [])

    # If no media arrays exist, fall back to counting content_blocks (old data)
    if not image_count and content_blocks:
        image_count = count_blocks('image')
    if not audio_count and content_blocks:
        audio_count = count_blocks('audio')
    if not video_count and content_blocks:
        # Only count actual video blocks (youtube_embed/vimeo_embed are NOT downloaded videos)
        # When YouTube/Vimeo videos are downloaded, they become 'video' blocks
        video_count = count_blocks('video')

    comment_block_count = count_blocks('comment')

    comments_count = metadata.get('comments_count') or comment_block_count

    # Check for published date in multiple locations (PostgreSQL vs JSON structure)
    published_raw = (
        post.get('published_date') or  # PostgreSQL direct field
        metadata.get('published_date') or  # JSON nested field
        post.get('published_at') or  # PostgreSQL timestamp
        ''
    )
    if isinstance(published_raw, str):
        published_raw = published_raw.strip()
    else:
        published_raw = str(published_raw) if published_raw else ''

    # Format the date for display
    published_label = format_date_eu(published_raw) if published_raw else format_date_eu(post.get('created_at'))
    if not published_label or published_label == 'N/A':
        published_label = 'Date unknown'

    date_skip_originals = set()
    if published_raw:
        date_skip_originals.add(published_raw.strip())
        formatted_raw = format_date_eu(published_raw)
        if formatted_raw:
            date_skip_originals.add(formatted_raw)

    created_formatted = format_date_eu(post.get('created_at'))
    if created_formatted:
        date_skip_originals.add(created_formatted)

    date_skip_originals.add(published_label)
    date_skip_originals = {s for s in date_skip_originals if isinstance(s, str) and s.strip()}
    date_skip_lower = {s.lower() for s in date_skip_originals}

    def ensure_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def filter_by_extension(values, extensions):
        if not values:
            return []
        cleaned = []
        for entry in ensure_list(values):
            if not entry:
                continue
            entry_str = str(entry).replace('\\', '/')
            if not extensions or any(entry_str.lower().endswith(ext) for ext in extensions):
                cleaned.append(entry_str)
        return cleaned

    # Note: video_local_paths already sorted and updated above (line 630)
    # local_video_paths = filter_by_extension(post.get('video_local_paths'), {'.mp4', '.m4v', '.mov', '.webm', '.mkv'})
    local_audio_paths = filter_by_extension(post.get('audio_local_paths'), {'.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus'})

    # post['video_local_paths'] = local_video_paths  # Already sorted above, don't overwrite
    post['audio_local_paths'] = local_audio_paths

    # Get collection info for "back to collection" button
    collection_info = None
    if from_collection_id:
        for collection in post.get('collections', []):
            if collection.get('collection_id') == from_collection_id:
                collection_info = collection
                break

    return render_template(
        'post.html',
        post=post,
        creator_display_name=creator_display_name,
        creator_avatar=creator_avatar,
        likes_count=likes_count,
        comments_count=comments_count,
        image_count=image_count,
        video_count=video_count,
        audio_count=audio_count,
        attachment_count=attachment_count,
        has_images=image_count > 0,
        has_videos=video_count > 0,
        has_audio=audio_count > 0,
        has_attachments=attachment_count > 0,
        published_label=published_label,
        date_skip_values=sorted(date_skip_originals),
        date_skip_values_lower=sorted(date_skip_lower),
        from_collection_id=from_collection_id,
        from_creator_id=from_creator_id,
        collection_info=collection_info,
    )


@app.route('/creator/<creator_id>')
def view_creator(creator_id):
    """View all posts from a creator"""
    posts = load_all_posts()

    # Filter by creator
    creator_posts = [p for p in posts if p.get('creator_id') == creator_id]

    # Use local avatar image instead of Patreon URL
    creator_avatar = None
    if creator_id in CREATOR_AVATARS:
        creator_avatar = f"/static/{CREATOR_AVATARS[creator_id]}"
    # NOTE: Removed fallback to post['creator_avatar'] - inconsistent across posts

    # Build avatar paths ONLY from CREATOR_AVATARS (single source of truth)
    creator_avatars = {}
    for post in creator_posts:
        cid = post.get('creator_id', 'unknown')
        if cid not in creator_avatars and cid in CREATOR_AVATARS:
            creator_avatars[cid] = f"/static/{CREATOR_AVATARS[cid]}"
        # NOTE: Removed fallback to post['creator_avatar'] - too inconsistent

    return render_template('creator.html',
                          creator_id=creator_id,
                          creator_avatar=creator_avatar,
                          creator_avatars=creator_avatars,
                          posts=creator_posts)


@app.route('/tag/<tag_name>')
def view_tag(tag_name):
    """View all posts with a specific tag"""
    posts = load_all_posts()

    # Filter posts that have this tag and group by creator
    tagged_posts = []
    creators_with_tag = {}  # {creator_id: [posts]}
    creator_avatars = {}  # Build local dict with full paths

    for post in posts:
        tags = post.get('patreon_tags', [])
        if tag_name in tags:
            # Set display name using same logic as index and view_post
            metadata = post.get('post_metadata') or {}
            creator_id = post.get('creator_id', 'unknown')
            creator_display_name = metadata.get('creator_name') or get_creator_display_name(creator_id)
            if not creator_display_name:
                creator_display_name = creator_id or "Unknown Creator"
            post['display_creator_name'] = creator_display_name

            tagged_posts.append(post)

            # Group by creator
            if creator_id not in creators_with_tag:
                creators_with_tag[creator_id] = []
            creators_with_tag[creator_id].append(post)

            # Build avatar paths ONLY from CREATOR_AVATARS (single source of truth)
            if creator_id not in creator_avatars:
                if creator_id in CREATOR_AVATARS:
                    creator_avatars[creator_id] = f"/static/{CREATOR_AVATARS[creator_id]}"
                # NOTE: Removed fallback to post['creator_avatar'] - too inconsistent

    # Load creator colors from config
    creators_config = load_creators_config()
    creator_colors = {c['creator_id']: c.get('preview_color', '#4db8a0') for c in creators_config}

    return render_template('tag.html',
                          tag=tag_name,
                          posts=tagged_posts,
                          creators=creators_with_tag,
                          creator_colors=creator_colors,
                          creator_avatars=creator_avatars,
                          total=len(tagged_posts))


@app.route('/collection/<creator_id>/<collection_id>')
def view_collection(creator_id, collection_id):
    """View all posts in a specific collection"""
    posts = load_all_posts()

    # Filter posts that belong to this collection
    collection_posts = []
    collection_info = None

    for post in posts:
        if post.get('creator_id') != creator_id:
            continue

        collections = post.get('collections', [])
        for collection in collections:
            if collection.get('collection_id') == collection_id:
                collection_posts.append(post)
                # Store collection info from first match
                if not collection_info:
                    collection_info = collection
                break

    # Get creator info
    creator_display_name = get_creator_display_name(creator_id)
    creator_avatar = None
    if creator_id in CREATOR_AVATARS:
        creator_avatar = f"/static/{CREATOR_AVATARS[creator_id]}"

    # Default collection info if not found
    if not collection_info:
        collection_info = {
            'collection_id': collection_id,
            'collection_name': f'Collection {collection_id}',
            'collection_image_local': None
        }

    # Load creator colors from config
    creators_config = load_creators_config()
    creator_colors = {c['creator_id']: c.get('preview_color', '#4db8a0') for c in creators_config}

    # Build avatar paths with /static/ prefix (same as index and tag)
    creator_avatars = {}
    for post in collection_posts:
        cid = post.get('creator_id', 'unknown')
        if cid not in creator_avatars:
            if cid in CREATOR_AVATARS:
                creator_avatars[cid] = f"/static/{CREATOR_AVATARS[cid]}"
            # NOTE: Removed fallback to post['creator_avatar'] - too inconsistent

    return render_template('collection.html',
                          creator_id=creator_id,
                          creator_display_name=creator_display_name,
                          creator_avatar=creator_avatar,
                          creator_avatars=creator_avatars,
                          collection=collection_info,
                          creator_colors=creator_colors,
                          posts=collection_posts,
                          total=len(collection_posts))


@app.route('/settings', methods=['GET'])
def settings():
    """Settings page for configuration and processing status"""
    config_dir = Path(__file__).parent.parent / "config"

    # Load credentials
    credentials = {}
    credentials_file = config_dir / "credentials.json"
    if credentials_file.exists():
        with open(credentials_file, 'r', encoding='utf-8') as f:
            credentials = json.load(f)

    # Load creators
    creators_list = []
    creators_file = config_dir / "creators.json"
    if creators_file.exists():
        with open(creators_file, 'r', encoding='utf-8') as f:
            creators_data = json.load(f)
            creators_list = creators_data.get('creators', [])

    # Try to load PostgreSQL stats if available
    db_stats = {}
    db_enabled = False
    print(f"🔍 DEBUG: POSTGRES_AVAILABLE = {POSTGRES_AVAILABLE}")
    if POSTGRES_AVAILABLE:
        try:
            print("🔍 DEBUG: Creating PostgresTracker...")
            tracker = PostgresTracker()
            print("🔍 DEBUG: Getting all_creator_stats...")
            all_stats = tracker.get_all_creator_stats()
            print(f"🔍 DEBUG: Got stats for {len(all_stats)} creators")
            db_stats = all_stats if all_stats else {}
            db_enabled = True
            print(f"🔍 DEBUG: db_enabled = True")
        except Exception as e:
            print(f"❌ Warning: Could not load PostgreSQL stats: {e}")
            import traceback
            traceback.print_exc()
            db_enabled = False

    # Get processing status for each creator
    processing_status = []
    for creator in creators_list:
        creator_id = creator['creator_id']

        # Get database stats if available
        creator_stats = db_stats.get(creator_id, {})
        phase1_total = creator_stats.get('total_posts', 0)
        phase1_pending = creator_stats.get('pending_posts', 0)
        phase1_processed = creator_stats.get('processed_posts', 0)

        # Check Phase 2: Posts detailed (from PostgreSQL)
        posts_count = 0
        posts_last_updated = None
        if db_enabled:
            try:
                # Query posts table for this creator using tracker's engine
                with tracker.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT
                            COUNT(*) as total,
                            MAX(updated_at) as last_updated
                        FROM posts
                        WHERE creator_id = :creator_id
                          AND deleted_at IS NULL
                          AND content_blocks IS NOT NULL
                    """), {'creator_id': creator_id})
                    row = result.fetchone()
                    if row:
                        posts_count = row[0]
                        if row[1]:
                            posts_last_updated = row[1].strftime('%d/%m/%Y %H:%M')
            except Exception as e:
                print(f"Warning: Could not load Phase 2 stats for {creator_id}: {e}")
                # Fallback to JSON
                posts_file = PROCESSED_DATA_DIR / f"{creator_id}_posts_detailed.json"
                if posts_file.exists():
                    try:
                        with open(posts_file, 'r', encoding='utf-8') as f:
                            posts_data = json.load(f)
                            posts_count = len(posts_data)
                        posts_last_updated = datetime.fromtimestamp(posts_file.stat().st_mtime).strftime('%d/%m/%Y %H:%M')
                    except:
                        pass

        # Check Phase 3: Collections (from PostgreSQL)
        collections_count = 0
        collections_last_updated = None
        if db_enabled:
            try:
                # Query collections table for this creator using tracker's engine
                with tracker.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT
                            COUNT(*) as total,
                            MAX(updated_at) as last_updated
                        FROM collections
                        WHERE creator_id = :creator_id
                          AND deleted_at IS NULL
                    """), {'creator_id': creator_id})
                    row = result.fetchone()
                    if row:
                        collections_count = row[0]
                        if row[1]:
                            collections_last_updated = row[1].strftime('%d/%m/%Y %H:%M')
            except Exception as e:
                print(f"Warning: Could not load Phase 3 stats for {creator_id}: {e}")
                # Fallback to JSON
                collections_file = PROCESSED_DATA_DIR / f"{creator_id}_collections.json"
                if collections_file.exists():
                    try:
                        with open(collections_file, 'r', encoding='utf-8') as f:
                            collections_data = json.load(f)
                            collections_count = len(collections_data.get('collections', []))
                        collections_last_updated = datetime.fromtimestamp(collections_file.stat().st_mtime).strftime('%d/%m/%Y %H:%M')
                    except:
                        pass

        processing_status.append({
            'creator_id': creator_id,
            'creator_name': creator['name'],
            'creator_url': creator['url'],
            'phase1_total': phase1_total,
            'phase1_pending': phase1_pending,
            'phase1_processed': phase1_processed,
            'phase1_status': 'Configured' if creator['url'] else 'Not configured',
            'phase2_posts': posts_count,
            'phase2_last_updated': posts_last_updated,
            'phase3_collections': collections_count,
            'phase3_last_updated': collections_last_updated
        })

    return render_template('settings.html',
                          credentials=credentials,
                          creators=creators_list,
                          processing_status=processing_status,
                          db_enabled=db_enabled)


@app.route('/api/settings/save', methods=['POST'])
def save_settings():
    """Save configuration from settings page - ONLY saves credentials, NOT creators"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        data = request.get_json()

        # CRITICAL: This endpoint ONLY saves credentials
        # Creators are managed by /api/creator/* endpoints

        if 'credentials' not in data:
            return jsonify({
                'success': False,
                'message': 'No credentials data provided'
            }), 400

        credentials = data['credentials']

        # Validate that credentials have ALL required fields
        patreon = credentials.get('patreon', {})

        # Strict validation - ALL fields must be present and non-empty
        if not patreon.get('email') or not patreon.get('password'):
            return jsonify({
                'success': False,
                'message': 'ERROR: Patreon email and password are required. Not saving to prevent data loss.'
            }), 400

        # Additional safety: check if credentials.json exists and compare
        credentials_file = config_dir / "credentials.json"
        if credentials_file.exists():
            # Load existing to compare
            with open(credentials_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)

            # If new credentials are "worse" than existing, reject
            existing_patreon = existing.get('patreon', {})
            if existing_patreon.get('email') and not patreon.get('email'):
                return jsonify({
                    'success': False,
                    'message': 'ERROR: Cannot replace existing credentials with empty ones'
                }), 400

            # Create backup before overwriting
            backup_file = credentials_file.with_suffix('.json.backup')
            import shutil
            shutil.copy2(credentials_file, backup_file)
            print(f"✅ Created backup: {backup_file}")

        # Save credentials
        with open(credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2)

        return jsonify({
            'success': True,
            'message': 'Credentials saved successfully. Backup created.',
            'backup_created': True
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving credentials: {str(e)}'
        }), 500


@app.route('/api/media-settings/get', methods=['GET'])
def get_media_settings():
    """Get media download settings from settings.json"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        settings_file = config_dir / "settings.json"

        if not settings_file.exists():
            # Return default settings
            return jsonify({
                'success': True,
                'settings': {
                    "media": {
                        "images": {
                            "download_content_images": True,
                            "skip_avatars": True,
                            "skip_covers": True,
                            "skip_thumbnails": True,
                            "min_size": {"width": 400, "height": 400},
                            "deduplication": True
                        },
                        "patreon": {
                            "videos": {"download": True, "quality": "best", "format": "mp4"},
                            "audios": {"download": True, "format": "mp3"}
                        },
                        "youtube": {"mode": "embed"},
                        "deduplication": {"enabled": True, "hash_algorithm": "sha256"}
                    }
                }
            })

        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        return jsonify({
            'success': True,
            'settings': settings
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading settings: {str(e)}'
        }), 500


@app.route('/api/media-settings/save', methods=['POST'])
def save_media_settings():
    """Save media download settings to settings.json"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        settings_file = config_dir / "settings.json"

        data = request.get_json()

        if 'settings' not in data:
            return jsonify({
                'success': False,
                'message': 'No settings data provided'
            }), 400

        # Create backup if file exists
        if settings_file.exists():
            backup_file = settings_file.with_suffix('.json.backup')
            import shutil
            shutil.copy2(settings_file, backup_file)
            print(f"✅ Created backup: {backup_file}")

        # Save new settings
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data['settings'], f, indent=2, ensure_ascii=False)

        print(f"✅ Saved media settings to: {settings_file}")

        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving settings: {str(e)}'
        }), 500


@app.route('/api/creator/update', methods=['POST'])
def update_creator():
    """Update an existing creator in creators.json"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        creators_file = config_dir / "creators.json"

        # Load existing creators
        with open(creators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        creators_list = data.get('creators', [])
        updated_creator = request.get_json()

        # Find and update the creator
        found = False
        for i, creator in enumerate(creators_list):
            if creator['creator_id'] == updated_creator['creator_id']:
                creators_list[i] = updated_creator
                found = True
                break

        if not found:
            return jsonify({'success': False, 'message': 'Creator not found'}), 404

        # Save back to file
        data['creators'] = creators_list
        with open(creators_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return jsonify({'success': True, 'message': 'Creator updated successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/creator/add', methods=['POST'])
def add_creator():
    """Add a new creator to creators.json"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        creators_file = config_dir / "creators.json"

        # Load existing creators
        with open(creators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        creators_list = data.get('creators', [])
        new_creator = request.get_json()

        # Check if creator ID already exists
        for creator in creators_list:
            if creator['creator_id'] == new_creator['creator_id']:
                return jsonify({'success': False, 'message': 'Creator ID already exists'}), 400

        # Add new creator
        creators_list.append(new_creator)

        # Save back to file
        data['creators'] = creators_list
        with open(creators_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return jsonify({'success': True, 'message': 'Creator added successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/creator/delete', methods=['POST'])
def delete_creator():
    """Delete a creator from creators.json"""
    try:
        config_dir = Path(__file__).parent.parent / "config"
        creators_file = config_dir / "creators.json"

        # Load existing creators
        with open(creators_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        creators_list = data.get('creators', [])
        creator_id_to_delete = request.get_json().get('creator_id')

        # Remove the creator
        creators_list = [c for c in creators_list if c['creator_id'] != creator_id_to_delete]

        # Save back to file
        data['creators'] = creators_list
        with open(creators_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return jsonify({'success': True, 'message': 'Creator deleted successfully'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/creator/upload-avatar', methods=['POST'])
def upload_avatar():
    """Upload avatar image for a creator"""
    try:
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400

        file = request.files['avatar']
        creator_id = request.form.get('creator_id')

        if not creator_id:
            return jsonify({'success': False, 'message': 'Creator ID is required'}), 400

        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        # Get file extension
        ext = Path(file.filename).suffix.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            return jsonify({'success': False, 'message': 'Invalid file type. Use JPG, PNG, WebP, or GIF'}), 400

        # Save to static directory
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)

        filename = f"{creator_id}{ext}"
        filepath = static_dir / filename

        file.save(str(filepath))

        return jsonify({'success': True, 'avatar_filename': filename})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/creator/reset-posts', methods=['POST'])
def reset_creator_posts():
    """Reset all posts from a creator to pending status in PostgreSQL"""
    try:
        data = request.json
        creator_id = data.get('creator_id')

        if not creator_id:
            return jsonify({'success': False, 'message': 'Creator ID is required'}), 400

        # Check if PostgreSQL is enabled
        if not use_postgresql():
            return jsonify({'success': False, 'message': 'PostgreSQL mode not enabled'}), 400

        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Count posts to reset (from scraping_status table)
            count_sql = text("""
                SELECT COUNT(*)
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                WHERE cs.platform_id = :creator_id
            """)
            result = conn.execute(count_sql, {'creator_id': creator_id})
            total = result.fetchone()[0]

            if total == 0:
                return jsonify({'success': False, 'message': f'No posts found for creator "{creator_id}"'}), 404

            # Reset phase2 status to pending so phase2_detail_extractor will reprocess them
            reset_sql = text("""
                UPDATE scraping_status
                SET phase2_status = 'pending',
                    phase2_completed_at = NULL,
                    phase2_attempts = 0,
                    phase2_last_error = NULL,
                    updated_at = NOW()
                WHERE source_id IN (
                    SELECT id FROM creator_sources
                    WHERE platform_id = :creator_id
                )
            """)
            conn.execute(reset_sql, {'creator_id': creator_id})

            # Soft-delete posts so they disappear from index until reprocessed
            delete_sql = text("""
                UPDATE posts
                SET deleted_at = NOW()
                WHERE creator_id = :creator_id
            """)
            conn.execute(delete_sql, {'creator_id': creator_id})

            conn.commit()

            return jsonify({
                'success': True,
                'reset_count': total,
                'creator_id': creator_id,
                'message': f'Successfully reset {total} posts for {creator_id}'
            })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/posts')
def api_posts():
    """API endpoint to get all posts as JSON"""
    posts = load_all_posts()
    return jsonify(posts)


def api_collections_from_postgres(creator_filter=None):
    """Fast PostgreSQL-based collections API (100x faster than JSON method)"""
    from sqlalchemy import create_engine, text

    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Build WHERE clause for creator filter
        where_clause = "WHERE c.deleted_at IS NULL"
        params = {}

        if creator_filter:
            creators = [c.strip() for c in creator_filter.split(',')]
            where_clause += " AND c.creator_id = ANY(:creators)"
            params['creators'] = creators

        # Optimized SQL query with aggregations
        query = text(f"""
            SELECT
                c.collection_id,
                c.title as collection_name,
                c.collection_url,
                c.collection_image_local,
                c.creator_id,
                COUNT(DISTINCT pc.post_id) as post_count,
                COALESCE(SUM(p.like_count), 0) as total_likes,
                COALESCE(SUM(p.comment_count), 0) as total_comments,
                COALESCE(SUM(CASE WHEN array_length(p.video_local_paths, 1) > 0 THEN array_length(p.video_local_paths, 1) ELSE 0 END), 0) as total_videos,
                COALESCE(SUM(CASE WHEN array_length(p.audio_local_paths, 1) > 0 THEN array_length(p.audio_local_paths, 1) ELSE 0 END), 0) as total_audios,
                COALESCE(SUM(CASE WHEN array_length(p.image_local_paths, 1) > 0 THEN array_length(p.image_local_paths, 1) ELSE 0 END), 0) as total_images,
                MAX(p.published_at) as latest_post_date,
                ARRAY_AGG(pc.post_id ORDER BY pc.order_in_collection) FILTER (WHERE pc.post_id IS NOT NULL) as post_ids,
                MAX(p.creator_name) as creator_name
            FROM collections c
            LEFT JOIN post_collections pc ON c.collection_id = pc.collection_id
            LEFT JOIN posts p ON pc.post_id = p.post_id AND p.deleted_at IS NULL
            {where_clause}
            GROUP BY c.collection_id, c.title, c.collection_url, c.collection_image_local, c.creator_id
            ORDER BY latest_post_date DESC NULLS LAST
        """)

        result = conn.execute(query, params)
        rows = result.fetchall()

        collections_list = []
        for row in rows:
            collections_list.append({
                'collection_id': row[0],
                'collection_name': row[1],
                'collection_url': row[2],
                'collection_image_local': row[3],
                'creator_id': row[4],
                'post_count': row[5],
                'total_likes': row[6],
                'total_comments': row[7],
                'total_videos': row[8],
                'total_audios': row[9],
                'total_images': row[10],
                'latest_post_date': row[11].isoformat() if row[11] else None,
                'post_ids': row[12] if row[12] else [],
                'creator_name': row[13]
            })

        return jsonify({
            'total_collections': len(collections_list),
            'collections': collections_list
        })


@app.route('/api/collections')
def api_collections():
    """
    API endpoint to get collections with aggregated post stats
    Query params:
        creator: filter by creator_id (optional, can be comma-separated for multiple)
    Returns collections with:
        - collection metadata
        - latest_post_date
        - total likes, comments, videos, audios
        - post count
        - post_ids array
    """
    creator_filter = request.args.get('creator')

    # Fast path: Use PostgreSQL if available
    if use_postgresql():
        try:
            return api_collections_from_postgres(creator_filter)
        except Exception as e:
            logger.error(f"Error loading collections from PostgreSQL: {e}")
            # Fallback to JSON method below

    # Slow path: Load all posts and aggregate (for JSON mode)
    posts = load_all_posts()

    # Filter by creator if specified (support multiple creators)
    if creator_filter:
        creators = [c.strip() for c in creator_filter.split(',')]
        posts = [p for p in posts if p.get('creator_id') in creators]

    # Group posts by collection
    collections_map = {}

    for post in posts:
        post_collections = post.get('collections', [])

        # Skip posts without collections
        if not post_collections:
            continue

        post_id = post.get('post_id')
        published = post.get('published_date')
        likes = post.get('likes_count', 0) or 0
        comments = post.get('comments_count', 0) or 0

        # Count media
        videos_count = len(post.get('video_local_paths', []) or [])
        audios_count = len(post.get('audio_local_paths', []) or [])
        images_count = len(post.get('image_local_paths', []) or [])

        for collection in post_collections:
            coll_id = collection.get('collection_id')
            if not coll_id:
                continue

            # Initialize collection if not exists
            if coll_id not in collections_map:
                collections_map[coll_id] = {
                    'collection_id': coll_id,
                    'collection_name': collection.get('collection_name', 'Unnamed Collection'),
                    'collection_url': collection.get('collection_url'),
                    'collection_image_local': collection.get('collection_image_local'),
                    'creator_id': post.get('creator_id'),
                    'creator_name': post.get('creator_name'),
                    'post_ids': [],
                    'post_count': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_videos': 0,
                    'total_audios': 0,
                    'total_images': 0,
                    'latest_post_date': None
                }

            # Aggregate stats
            coll = collections_map[coll_id]
            if post_id not in coll['post_ids']:
                coll['post_ids'].append(post_id)
                coll['post_count'] += 1
                coll['total_likes'] += likes
                coll['total_comments'] += comments
                coll['total_videos'] += videos_count
                coll['total_audios'] += audios_count
                coll['total_images'] += images_count

                # Update latest date
                if published:
                    if not coll['latest_post_date'] or published > coll['latest_post_date']:
                        coll['latest_post_date'] = published

    # Convert to list and sort by latest_post_date
    collections_list = list(collections_map.values())
    collections_list.sort(key=lambda x: x.get('latest_post_date') or '', reverse=True)

    return jsonify({
        'total_collections': len(collections_list),
        'collections': collections_list
    })


@app.route('/api/post/<post_id>')
def api_post(post_id):
    """API endpoint to get single post"""
    posts = load_all_posts()

    for p in posts:
        if p.get('post_id') == post_id:
            return jsonify(p)

    return jsonify({'error': 'Post not found'}), 404


@app.route('/api/search')
def api_search():
    """
    Advanced search endpoint using PostgreSQL Full-Text Search
    Falls back to SQLite FTS5 if PostgreSQL fails

    Query params:
        q: search query (required)
        creator: filter by creator_id (optional)
        limit: max results (default 50)
    """
    # Get query parameters
    query = request.args.get('q', '').strip()
    creator_filter = request.args.get('creator')
    limit = int(request.args.get('limit', 50))

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    # Try PostgreSQL first (modern, automatic)
    try:
        results = search_posts_postgresql(query, limit=limit, creator_filter=creator_filter)

        return jsonify({
            'query': query,
            'total_results': len(results),
            'results': results,
            'source': 'postgresql'  # Debug: show which backend was used
        })

    except Exception as pg_error:
        print(f"⚠️  PostgreSQL search failed: {pg_error}")
        print("   Falling back to SQLite FTS5...")

        # Fallback to SQLite FTS5 (legacy)
        from pathlib import Path
        import sys

        search_module_path = Path(__file__).parent
        if str(search_module_path) not in sys.path:
            sys.path.insert(0, str(search_module_path))

        try:
            from search_indexer import SearchIndexer
        except ImportError:
            return jsonify({
                'error': 'Both PostgreSQL and SQLite search failed',
                'postgresql_error': str(pg_error),
                'sqlite_error': 'Search indexer not available'
            }), 503

        # Check if SQLite index exists
        index_path = Path(__file__).parent / "search_index.db"
        if not index_path.exists():
            return jsonify({
                'error': 'Both PostgreSQL and SQLite search failed',
                'postgresql_error': str(pg_error),
                'sqlite_error': 'Search index not built. Run: python web/search_indexer.py'
            }), 503

        # Perform SQLite search
        try:
            indexer = SearchIndexer(db_path=index_path)
            results = indexer.search(query, limit=limit, creator_filter=creator_filter)
            indexer.close()

            return jsonify({
                'query': query,
                'total_results': len(results),
                'results': results,
                'source': 'sqlite'  # Debug: show fallback was used
            })

        except Exception as sqlite_error:
            return jsonify({
                'error': 'Both PostgreSQL and SQLite search failed',
                'postgresql_error': str(pg_error),
                'sqlite_error': str(sqlite_error)
            }), 500


@app.route('/api/search/stats')
def api_search_stats():
    """Get search index statistics"""
    from pathlib import Path
    import sys

    search_module_path = Path(__file__).parent
    if str(search_module_path) not in sys.path:
        sys.path.insert(0, str(search_module_path))

    try:
        from search_indexer import SearchIndexer
    except ImportError:
        return jsonify({'error': 'Search indexer not available'}), 503

    index_path = Path(__file__).parent / "search_index.db"
    if not index_path.exists():
        return jsonify({'error': 'Search index not built'}), 404

    try:
        indexer = SearchIndexer(db_path=index_path)
        stats = indexer.get_stats()
        indexer.close()

        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/media/<path:filename>')
def media_file(filename):
    """
    Serve downloaded media files with hash-based filename fallback.

    Supports optional 'original' query parameter to set download filename.
    Files are stored with hash-based names for deduplication, but can be
    downloaded with original filenames using Content-Disposition header.

    Args:
        filename: Relative path to media file (e.g., 'images/creator/hash_postid.jpg')

    Query Parameters:
        original: Optional original filename for downloads (e.g., 'photo.jpg')

    Returns:
        Flask response with file content and appropriate headers

    Examples:
        /media/images/creator/abc123_456789.jpg
        /media/audio/creator/def456_789012.mp3?original=podcast.mp3
    """
    from flask import request
    safe_path = (MEDIA_ROOT / filename).resolve()

    # If file doesn't exist, try to find it with hash prefix
    if not safe_path.exists():
        # Extract post_id from filename (e.g., "141079936" from "audio/astrobymax/141079936_00_1.mp3")
        import re
        from pathlib import Path

        # Try to extract post_id pattern (numbers followed by underscore)
        match = re.search(r'/(\d{8,})_', filename)
        if match:
            post_id = match.group(1)
            parent_dir = (MEDIA_ROOT / filename).parent

            if parent_dir.exists():
                # Look for files containing the post_id
                matching_files = list(parent_dir.glob(f"*{post_id}*"))
                if matching_files:
                    # Use the first match
                    safe_path = matching_files[0].resolve()

    if not safe_path.exists() or MEDIA_ROOT not in safe_path.parents and safe_path != MEDIA_ROOT:
        return "File not found", 404
    relative = safe_path.relative_to(MEDIA_ROOT)

    # Set correct MIME type for VTT subtitle files
    mimetype = None
    if filename.lower().endswith('.vtt'):
        mimetype = 'text/vtt'

    response = send_from_directory(MEDIA_ROOT, str(relative), mimetype=mimetype)

    # If 'original' parameter is provided, use it as download filename
    original_name = request.args.get('original')
    if original_name:
        response.headers['Content-Disposition'] = f'inline; filename="{original_name}"'

    # Add CORS headers for subtitle files to work properly
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response


# ============================================================================
# API Endpoints for Cache Management
# ============================================================================

@app.route('/api/cache/clear', methods=['POST', 'GET'])
def clear_cache():
    """Clear all cache - useful after processing new posts"""
    try:
        cache.clear()
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    try:
        return jsonify({
            'success': True,
            'cache_type': app.config['CACHE_TYPE'],
            'cache_timeout': app.config['CACHE_DEFAULT_TIMEOUT'],
            'message': 'Cache is active and working'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Patreon Content Viewer")
    print("=" * 60)
    print(f"📁 Raw data: {RAW_DATA_DIR}")
    print(f"📁 Processed data: {PROCESSED_DATA_DIR}")

    # Load creators config and build CREATOR_AVATARS
    creators = load_creators_config()
    print(f"👥 Loaded {len(creators)} creators with avatars: {list(CREATOR_AVATARS.keys())}")

    posts = load_all_posts()
    print(f"📄 Loaded {len(posts)} posts")

    if posts:
        print("\nPosts loaded:")
        for p in posts[:5]:
            print(f"  - {p.get('title', 'Untitled')} ({p.get('post_id', 'N/A')})")
        if len(posts) > 5:
            print(f"  ... and {len(posts) - 5} more")

    print()
    print("🚀 Starting server at http://localhost:5000")
    print("   Press Ctrl+C to stop")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
