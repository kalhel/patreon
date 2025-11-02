#!/usr/bin/env python3
"""
Web Viewer - Local web app to preview scraped Patreon posts
Displays posts with formatting similar to Patreon before uploading to Notion
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Data directories - try both raw and processed
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# Display names for creators
CREATOR_DISPLAY_NAMES = {
    'headonhistory': 'Ali A Olomi',
    'horoiproject': 'horoiproject',
    'astrobymax': 'astrobymax'
}


def format_date_eu(date_str):
    """Convert YYYY-MM-DD to DD-MM-YYYY"""
    if not date_str:
        return 'N/A'
    try:
        # Handle both YYYY-MM-DD and datetime strings
        if 'T' in str(date_str):
            date_str = date_str.split('T')[0]

        parts = str(date_str).split('-')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str
    except:
        return str(date_str)


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

        # Store first avatar found for this creator
        if creator_id not in creator_avatars and post.get('creator_avatar'):
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

    return render_template('post.html', post=post)


@app.route('/creator/<creator_id>')
def view_creator(creator_id):
    """View all posts from a creator"""
    posts = load_all_posts()

    # Filter by creator
    creator_posts = [p for p in posts if p.get('creator_id') == creator_id]

    # Get avatar
    creator_avatar = None
    for post in creator_posts:
        if post.get('creator_avatar'):
            creator_avatar = post['creator_avatar']
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
