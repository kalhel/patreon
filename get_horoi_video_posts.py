#!/usr/bin/env python3
"""
Extract horoiproject post IDs that have videos
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from firebase_tracker import load_firebase_config, FirebaseTracker

def main():
    # Load Firebase config
    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    print("🔍 Querying Firebase for horoiproject posts with videos...\n", flush=True)

    # Get all posts from Firebase
    all_posts = tracker._get('posts')

    if not all_posts:
        print("❌ No posts found in Firebase")
        return

    # Filter horoiproject posts with videos
    video_post_ids = []

    for post_id, post_data in all_posts.items():
        creator_id = post_data.get('creator_id', '')

        if creator_id != 'horoiproject':
            continue

        # Check if post has videos
        post_detail = post_data.get('post_detail', {})

        has_video = False

        # Check for video streams/downloads
        if post_detail.get('video_streams') or post_detail.get('video_downloads'):
            has_video = True

        # Check content blocks for video/youtube
        if not has_video and post_detail.get('content_blocks'):
            has_video = any(b.get('type') in ['video', 'youtube_embed']
                          for b in post_detail.get('content_blocks', []))

        if has_video:
            title = post_detail.get('title', 'Sin título')[:50]
            video_post_ids.append({
                'post_id': post_id,
                'title': title
            })

    print(f"✅ Found {len(video_post_ids)} horoiproject posts with videos\n")

    if not video_post_ids:
        print("No videos found in horoiproject posts.")
        return

    # Sort by post_id
    video_post_ids.sort(key=lambda x: x['post_id'])

    print("=" * 80)
    print("COMMANDS TO REPROCESS EACH POST:")
    print("=" * 80)
    print()

    # Print individual commands
    for post in video_post_ids:
        print(f"# {post['title']}")
        print(f"python3 src/phase2_detail_extractor.py --post {post['post_id']} --headless")
        print()

    print("=" * 80)
    print("OR RUN ALL IN SEQUENCE:")
    print("=" * 80)
    print()

    # Print all IDs in one line for batch processing
    all_ids = [p['post_id'] for p in video_post_ids]
    print("# Run all posts (copy and paste this):")
    for post_id in all_ids:
        print(f"python3 src/phase2_detail_extractor.py --post {post_id} --headless && \\")

    # Print last one without &&
    print()
    print(f"# Total: {len(video_post_ids)} posts to reprocess")

if __name__ == '__main__':
    main()
