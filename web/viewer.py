#!/usr/bin/env python3
"""
Web Viewer - Local web app to preview scraped Patreon posts
Displays posts with formatting similar to Patreon before uploading to Notion
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Data directories - try both raw and processed
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
MEDIA_ROOT = Path(__file__).parent.parent / "data" / "media"

# Display names for creators
CREATOR_DISPLAY_NAMES = {
    'headonhistory': 'Ali A Olomi',
    'horoiproject': 'horoiproject',
    'astrobymax': 'astrobymax'
}

# Local avatar paths for creators
CREATOR_AVATARS = {
    'headonhistory': 'headonhistory.jpg',
    'horoiproject': 'horoiproject.jpg',
    'astrobymax': 'astrobymax.jpg'
}


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


# Register Jinja filters
app.jinja_env.filters['date_eu'] = format_date_eu
app.jinja_env.filters['creator_name'] = get_creator_display_name


def load_all_posts():
    """Load all posts from JSON files (raw and processed)"""
    all_posts = []

    # Try raw directory first
    if RAW_DATA_DIR.exists():
        for json_file in RAW_DATA_DIR.glob("*_posts.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    all_posts.extend(posts)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

    # Then try processed directory
    if PROCESSED_DATA_DIR.exists():
        for json_file in PROCESSED_DATA_DIR.glob("*_posts_detailed.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    all_posts.extend(posts)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")

    # Sort by post_id (newest first)
    all_posts.sort(key=lambda x: x.get('post_id', ''), reverse=True)

    return all_posts


@app.route('/')
def index():
    """Homepage showing all posts"""
    posts = load_all_posts()

    # Group by creator
    creators = {}
    creator_avatars = {}
    for post in posts:
        creator_id = post.get('creator_id', 'unknown')
        if creator_id not in creators:
            creators[creator_id] = []
        creators[creator_id].append(post)

        if creator_id not in creator_avatars:
            if creator_id in CREATOR_AVATARS:
                creator_avatars[creator_id] = f"/static/{CREATOR_AVATARS[creator_id]}"
            elif post.get('creator_avatar'):
                creator_avatars[creator_id] = post['creator_avatar']

    return render_template('index.html',
                          creators=creators,
                          creator_avatars=creator_avatars,
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

    metadata = post.get('post_metadata') or {}
    creator_id = post.get('creator_id', 'unknown')
    creator_display_name = metadata.get('creator_name') or get_creator_display_name(creator_id)
    if not creator_display_name:
        creator_display_name = creator_id or "Unknown Creator"

    creator_avatar = None
    if creator_id in CREATOR_AVATARS:
        creator_avatar = f"/static/{CREATOR_AVATARS[creator_id]}"
    elif metadata.get('creator_avatar'):
        creator_avatar = metadata['creator_avatar']

    likes_count = metadata.get('likes_count') or 0
    comments_count = metadata.get('comments_count') or 0
    published_label = metadata.get('published_date')
    if not published_label:
        published_label = format_date_eu(post.get('created_at'))

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

    local_video_paths = filter_by_extension(post.get('video_local_paths'), {'.mp4', '.m4v', '.mov', '.webm', '.mkv'})
    local_audio_paths = filter_by_extension(post.get('audio_local_paths'), {'.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus'})

    post['video_local_paths'] = local_video_paths
    post['audio_local_paths'] = local_audio_paths

    return render_template(
        'post.html',
        post=post,
        creator_display_name=creator_display_name,
        creator_avatar=creator_avatar,
        likes_count=likes_count,
        comments_count=comments_count,
        published_label=published_label,
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
    else:
        for post in creator_posts:
            candidate = post.get('creator_avatar')
            if not candidate:
                metadata = post.get('post_metadata') or {}
                candidate = metadata.get('creator_avatar')
            if candidate:
                creator_avatar = candidate
                break

    return render_template('creator.html',
                          creator_id=creator_id,
                          creator_avatar=creator_avatar,
                          posts=creator_posts)


@app.route('/tag/<tag_name>')
def view_tag(tag_name):
    """View all posts with a specific tag"""
    posts = load_all_posts()

    # Filter posts that have this tag
    tagged_posts = []
    for post in posts:
        tags = post.get('patreon_tags', [])
        if tag_name in tags:
            tagged_posts.append(post)

    return render_template('tag.html',
                          tag=tag_name,
                          posts=tagged_posts,
                          total=len(tagged_posts))


@app.route('/api/posts')
def api_posts():
    """API endpoint to get all posts as JSON"""
    posts = load_all_posts()
    return jsonify(posts)


@app.route('/api/post/<post_id>')
def api_post(post_id):
    """API endpoint to get single post"""
    posts = load_all_posts()

    for p in posts:
        if p.get('post_id') == post_id:
            return jsonify(p)

    return jsonify({'error': 'Post not found'}), 404


@app.route('/media/<path:filename>')
def media_file(filename):
    """Serve downloaded media files"""
    safe_path = (MEDIA_ROOT / filename).resolve()
    if not safe_path.exists() or MEDIA_ROOT not in safe_path.parents and safe_path != MEDIA_ROOT:
        return "File not found", 404
    relative = safe_path.relative_to(MEDIA_ROOT)
    return send_from_directory(MEDIA_ROOT, str(relative))


if __name__ == '__main__':
    print("=" * 60)
    print("🌐 Patreon Content Viewer")
    print("=" * 60)
    print(f"📁 Raw data: {RAW_DATA_DIR}")
    print(f"📁 Processed data: {PROCESSED_DATA_DIR}")

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
