#!/usr/bin/env python3
"""
Inspect horoiproject posts structure to understand data format
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from postgres_tracker import PostgresTracker

def main():
    # Initialize PostgreSQL tracker
    tracker = PostgresTracker()

    print("🔍 Inspecting horoiproject posts structure...\n", flush=True)

    # Get all posts from database
    all_posts = tracker.get_all_posts()

    if not all_posts:
        print("❌ No posts found in database")
        return

    # Find horoiproject posts
    horoi_posts = []
    for post_id, post_data in all_posts.items():
        creator_id = post_data.get('creator_id', '')
        if creator_id == 'horoiproject':
            horoi_posts.append((post_id, post_data))

    print(f"✅ Found {len(horoi_posts)} horoiproject posts\n")

    if not horoi_posts:
        print("No horoiproject posts found.")
        return

    # Sample first 3 posts to understand structure
    print("=" * 80)
    print("SAMPLE POST STRUCTURES (first 3):")
    print("=" * 80)

    for i, (post_id, post_data) in enumerate(horoi_posts[:3], 1):
        print(f"\n--- Post {i}: {post_id} ---")
        print(f"Keys in post_data: {list(post_data.keys())}")

        post_detail = post_data.get('post_detail', {})
        if post_detail:
            print(f"Keys in post_detail: {list(post_detail.keys())}")

            # Show title
            title = post_detail.get('title', 'Sin título')
            print(f"Title: {title[:70]}")

            # Check for video-related fields
            video_fields = {
                'videos': post_detail.get('videos'),
                'video_urls': post_detail.get('video_urls'),
                'video_streams': post_detail.get('video_streams'),
                'video_downloads': post_detail.get('video_downloads'),
                'video_local_paths': post_detail.get('video_local_paths'),
            }

            print("\nVideo-related fields:")
            for field, value in video_fields.items():
                if value:
                    if isinstance(value, list):
                        print(f"  {field}: {len(value)} items")
                        if value:
                            print(f"    Sample: {str(value[0])[:100]}")
                    else:
                        print(f"  {field}: {str(value)[:100]}")
                else:
                    print(f"  {field}: None/Empty")

            # Check content blocks
            content_blocks = post_detail.get('content_blocks', [])
            if content_blocks:
                block_types = {}
                for block in content_blocks:
                    btype = block.get('type', 'unknown')
                    block_types[btype] = block_types.get(btype, 0) + 1
                print(f"\nContent blocks: {len(content_blocks)} total")
                print(f"  Block types: {block_types}")

    # Count posts by presence of video indicators
    print("\n" + "=" * 80)
    print("VIDEO INDICATORS SUMMARY:")
    print("=" * 80)

    counts = {
        'video_streams': 0,
        'video_downloads': 0,
        'video_urls': 0,
        'videos': 0,
        'video_local_paths': 0,
        'content_block_video': 0,
        'content_block_youtube': 0,
    }

    for post_id, post_data in horoi_posts:
        post_detail = post_data.get('post_detail', {})

        if post_detail.get('video_streams'):
            counts['video_streams'] += 1
        if post_detail.get('video_downloads'):
            counts['video_downloads'] += 1
        if post_detail.get('video_urls'):
            counts['video_urls'] += 1
        if post_detail.get('videos'):
            counts['videos'] += 1
        if post_detail.get('video_local_paths'):
            counts['video_local_paths'] += 1

        content_blocks = post_detail.get('content_blocks', [])
        has_video_block = any(b.get('type') == 'video' for b in content_blocks)
        has_youtube_block = any(b.get('type') == 'youtube_embed' for b in content_blocks)

        if has_video_block:
            counts['content_block_video'] += 1
        if has_youtube_block:
            counts['content_block_youtube'] += 1

    print()
    for field, count in counts.items():
        print(f"{field:25s}: {count:4d} posts")

    # Find posts with ANY video indicator
    print("\n" + "=" * 80)
    print("POSTS WITH ANY VIDEO INDICATOR:")
    print("=" * 80)

    video_posts = []
    for post_id, post_data in horoi_posts:
        post_detail = post_data.get('post_detail', {})

        has_any_video = False
        reasons = []

        if post_detail.get('video_streams'):
            has_any_video = True
            reasons.append('video_streams')
        if post_detail.get('video_downloads'):
            has_any_video = True
            reasons.append('video_downloads')
        if post_detail.get('video_urls'):
            has_any_video = True
            reasons.append('video_urls')
        if post_detail.get('videos'):
            has_any_video = True
            reasons.append('videos')
        if post_detail.get('video_local_paths'):
            has_any_video = True
            reasons.append('video_local_paths')

        content_blocks = post_detail.get('content_blocks', [])
        if any(b.get('type') == 'video' for b in content_blocks):
            has_any_video = True
            reasons.append('video_block')
        if any(b.get('type') == 'youtube_embed' for b in content_blocks):
            has_any_video = True
            reasons.append('youtube_block')

        if has_any_video:
            title = post_detail.get('title', 'Sin título')[:60]
            video_posts.append({
                'post_id': post_id,
                'title': title,
                'reasons': reasons
            })

    print(f"\nTotal: {len(video_posts)} posts with video indicators\n")

    if video_posts:
        for post in video_posts[:10]:  # Show first 10
            print(f"{post['post_id']}: {post['title']}")
            print(f"  Indicators: {', '.join(post['reasons'])}")
            print()

        if len(video_posts) > 10:
            print(f"... and {len(video_posts) - 10} more posts")

if __name__ == '__main__':
    main()
