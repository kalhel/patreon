#!/usr/bin/env python3
"""
Extract horoiproject post IDs with videos from local JSON files
"""
import json
from pathlib import Path

def main():
    print("🔍 Searching for horoiproject posts with videos in local JSON files...\n")

    # Search for JSON files
    data_dirs = [
        Path('data/processed'),
        Path('data/raw'),
    ]

    all_posts = []

    for data_dir in data_dirs:
        if not data_dir.exists():
            continue

        for json_file in data_dir.glob('*horoiproject*.json'):
            print(f"📂 Loading {json_file}...")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_posts.extend(data)
                    elif isinstance(data, dict):
                        all_posts.append(data)
                print(f"   ✅ Loaded {len(data) if isinstance(data, list) else 1} posts")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    if not all_posts:
        print("\n❌ No horoiproject JSON files found!")
        print("\nSearched in:")
        print("  - data/processed/")
        print("  - data/raw/")
        return

    print(f"\n✅ Total posts loaded: {len(all_posts)}\n")

    # Find posts with videos
    video_posts = []

    for post in all_posts:
        post_id = post.get('post_id', 'unknown')
        title = post.get('title', 'Sin título')[:60]

        has_video = False
        reasons = []

        # Check various video indicators
        if post.get('video_streams'):
            has_video = True
            reasons.append(f"video_streams ({len(post['video_streams'])})")

        if post.get('video_downloads'):
            has_video = True
            reasons.append(f"video_downloads ({len(post['video_downloads'])})")

        if post.get('video_urls'):
            has_video = True
            reasons.append(f"video_urls ({len(post['video_urls'])})")

        if post.get('videos'):
            has_video = True
            reasons.append(f"videos ({len(post['videos'])})")

        # Check content blocks
        content_blocks = post.get('content_blocks', [])
        video_blocks = [b for b in content_blocks if b.get('type') == 'video']
        youtube_blocks = [b for b in content_blocks if b.get('type') == 'youtube_embed']

        if video_blocks:
            has_video = True
            reasons.append(f"video_blocks ({len(video_blocks)})")

        if youtube_blocks:
            has_video = True
            reasons.append(f"youtube_blocks ({len(youtube_blocks)})")

        if has_video:
            video_posts.append({
                'post_id': post_id,
                'title': title,
                'reasons': reasons
            })

    print("=" * 80)
    print(f"FOUND {len(video_posts)} POSTS WITH VIDEOS")
    print("=" * 80)
    print()

    if not video_posts:
        print("❌ No posts with videos found.")
        return

    # Sort by post_id
    video_posts.sort(key=lambda x: x['post_id'])

    print("Posts with videos:")
    print("-" * 80)
    for i, post in enumerate(video_posts, 1):
        print(f"{i:3d}. {post['post_id']}: {post['title']}")
        print(f"     Indicators: {', '.join(post['reasons'])}")

    print("\n" + "=" * 80)
    print("COMMANDS TO REPROCESS VIDEOS:")
    print("=" * 80)
    print()

    # Generate commands
    for post in video_posts:
        print(f"python3 src/phase2_detail_extractor.py --post {post['post_id']} --headless")

    print("\n" + "=" * 80)
    print("OR SAVE TO SCRIPT:")
    print("=" * 80)
    print()
    print("# Copy and paste to create reprocess_horoi_videos.sh:")
    print()
    print("cat > reprocess_horoi_videos.sh << 'EOF'")
    print("#!/bin/bash")
    print("set -e")
    print("source venv/bin/activate")
    print()
    for post in video_posts:
        print(f"echo 'Processing {post['post_id']}: {post['title']}'")
        print(f"python3 src/phase2_detail_extractor.py --post {post['post_id']} --headless")
        print()
    print("echo 'Done!'")
    print("EOF")
    print()
    print("chmod +x reprocess_horoi_videos.sh")
    print("./reprocess_horoi_videos.sh")

if __name__ == '__main__':
    main()
