#!/usr/bin/env python3
"""
Debug script to investigate video count issue for post 96242312
Shows "1 video" but original post has no videos
"""

import psycopg2
import json
import os
from dotenv import load_dotenv

def main():
    load_dotenv()

    print("=" * 80)
    print("DEBUG: Post 96242312 Video Count Investigation")
    print("=" * 80)
    print()

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'alejandria'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT post_id, title, videos, video_local_paths, content_blocks
        FROM posts
        WHERE post_id = '96242312'
    """)

    row = cursor.fetchone()

    if not row:
        print("✗ Post not found in database")
        conn.close()
        return

    post_id, title, videos_json, video_local_json, content_blocks_json = row

    print(f"Post ID: {post_id}")
    print(f"Title: {title}")
    print()

    # Parse JSON fields
    if isinstance(videos_json, str):
        videos = json.loads(videos_json) if videos_json else []
    else:
        videos = videos_json if videos_json else []

    if isinstance(video_local_json, str):
        video_local = json.loads(video_local_json) if video_local_json else []
    else:
        video_local = video_local_json if video_local_json else []

    if isinstance(content_blocks_json, str):
        content_blocks = json.loads(content_blocks_json) if content_blocks_json else []
    else:
        content_blocks = content_blocks_json if content_blocks_json else []

    print("-" * 80)
    print("1. SQL FIELDS")
    print("-" * 80)
    print(f"videos field: {len(videos)} items")
    if videos:
        for i, video_url in enumerate(videos, 1):
            print(f"  {i}. {video_url}")
    else:
        print("  (empty)")
    print()

    print(f"video_local_paths field: {len(video_local)} items")
    if video_local:
        for i, path in enumerate(video_local, 1):
            print(f"  {i}. {path}")
    else:
        print("  (empty)")
    print()

    # Check content_blocks for video-related blocks
    print("-" * 80)
    print("2. CONTENT BLOCKS")
    print("-" * 80)

    video_blocks = [b for b in content_blocks if b.get('type') == 'video']
    youtube_blocks = [b for b in content_blocks if b.get('type') == 'youtube_embed']
    vimeo_blocks = [b for b in content_blocks if b.get('type') == 'vimeo_embed']
    iframe_blocks = [b for b in content_blocks if b.get('type') == 'iframe']

    print(f"Video blocks: {len(video_blocks)}")
    if video_blocks:
        for i, block in enumerate(video_blocks, 1):
            print(f"  {i}. URL: {block.get('url', 'N/A')[:80]}...")
            print(f"     Order: {block.get('order', 'N/A')}")

    print(f"\nYouTube embed blocks: {len(youtube_blocks)}")
    if youtube_blocks:
        for i, block in enumerate(youtube_blocks, 1):
            print(f"  {i}. URL: {block.get('url', 'N/A')}")
            print(f"     Order: {block.get('order', 'N/A')}")

    print(f"\nVimeo embed blocks: {len(vimeo_blocks)}")
    if vimeo_blocks:
        for i, block in enumerate(vimeo_blocks, 1):
            print(f"  {i}. URL: {block.get('url', 'N/A')}")
            print(f"     Order: {block.get('order', 'N/A')}")

    print(f"\nIframe blocks: {len(iframe_blocks)}")
    if iframe_blocks:
        for i, block in enumerate(iframe_blocks, 1):
            print(f"  {i}. URL: {block.get('url', 'N/A')[:80]}...")
            print(f"     Order: {block.get('order', 'N/A')}")
    print()

    # Show how templates count videos
    print("-" * 80)
    print("3. HOW TEMPLATES COUNT VIDEOS")
    print("-" * 80)

    # Filter videos field to only count actual video files
    video_extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.m4v', '.mkv', '.m3u8', '.ts')
    actual_videos = [v for v in videos if any(v.lower().split('?')[0].endswith(ext) for ext in video_extensions)]

    print("Index/post logic:")
    print(f"  videos field (all items): {len(videos)}")
    print(f"  videos field (filtered for actual video extensions): {len(actual_videos)}")
    print(f"  video_local_paths: {len(video_local)}")

    # Count logic from templates
    vid_count_local = len(video_local)
    vid_count_filtered = len(actual_videos)
    vid_count = vid_count_local if vid_count_local > 0 else vid_count_filtered

    print(f"\n  Final count (prioritize local): {vid_count}")

    # Content block fallback
    content_video_count = len(video_blocks) + len(youtube_blocks)
    print(f"  Fallback from content_blocks: {content_video_count}")
    print()

    # Show problematic URLs if any
    if videos and not actual_videos:
        print("-" * 80)
        print("4. PROBLEM: videos field has URLs but none are video files!")
        print("-" * 80)
        print("These URLs in 'videos' field are NOT video files:")
        for i, url in enumerate(videos, 1):
            # Determine what type of file this is
            url_lower = url.lower().split('?')[0]
            if url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                file_type = "IMAGE"
            elif url_lower.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                file_type = "AUDIO"
            else:
                file_type = "UNKNOWN"
            print(f"  {i}. [{file_type}] {url}")

    conn.close()

if __name__ == '__main__':
    main()
