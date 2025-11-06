#!/usr/bin/env python3
"""
Debug script to check creator post distribution
"""
import json
from pathlib import Path
from collections import defaultdict

# Data directories
RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).parent / "data" / "processed"

def load_all_posts():
    """Load all posts from JSON files"""
    all_posts = []

    # Try raw directory first
    if RAW_DATA_DIR.exists():
        print(f"✓ Found RAW_DATA_DIR: {RAW_DATA_DIR}")
        for json_file in RAW_DATA_DIR.glob("*_posts.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    print(f"  Loaded {len(posts)} posts from {json_file.name}")
                    all_posts.extend(posts)
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")
    else:
        print(f"✗ RAW_DATA_DIR does not exist: {RAW_DATA_DIR}")

    # Then try processed directory
    if PROCESSED_DATA_DIR.exists():
        print(f"\n✓ Found PROCESSED_DATA_DIR: {PROCESSED_DATA_DIR}")
        for json_file in PROCESSED_DATA_DIR.glob("*_posts_detailed.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
                    print(f"  Loaded {len(posts)} posts from {json_file.name}")
                    all_posts.extend(posts)
            except Exception as e:
                print(f"  Error loading {json_file}: {e}")
    else:
        print(f"✗ PROCESSED_DATA_DIR does not exist: {PROCESSED_DATA_DIR}")

    return all_posts

def main():
    print("="*60)
    print("CREATOR POST DISTRIBUTION DEBUG")
    print("="*60)

    posts = load_all_posts()
    print(f"\n📊 Total posts loaded: {len(posts)}\n")

    if not posts:
        print("❌ No posts found!")
        return

    # Group by creator
    creators = defaultdict(list)
    for post in posts:
        creator_id = post.get('creator_id', 'unknown')
        creators[creator_id].append(post)

    print("="*60)
    print("POSTS BY CREATOR")
    print("="*60)
    for creator_id in sorted(creators.keys()):
        post_count = len(creators[creator_id])
        print(f"{creator_id}: {post_count} posts")

        # Show sample post IDs
        sample_posts = creators[creator_id][:3]
        for post in sample_posts:
            post_id = post.get('post_id', 'N/A')
            title = post.get('title', 'Untitled')[:50]
            print(f"  - {post_id}: {title}")

    print("="*60)

    # Check for headonhistory specifically
    if 'headonhistory' in creators:
        print(f"\n✅ headonhistory found with {len(creators['headonhistory'])} posts")
    else:
        print("\n❌ headonhistory NOT FOUND in creators!")
        print("   Available creators:", list(creators.keys()))

if __name__ == "__main__":
    main()
