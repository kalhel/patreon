#!/usr/bin/env python3
"""
Diagnose post creator_id issues
Finds posts that might have incorrect creator_id assignments
"""

import json
from pathlib import Path
from collections import defaultdict

# Post IDs to investigate
SUSPICIOUS_POST_IDS = ['96097452', '77933294', '42294201']

def diagnose_posts():
    """Find and diagnose suspicious posts"""

    data_dir = Path("data/processed")

    if not data_dir.exists():
        print("❌ data/processed directory doesn't exist")
        print("   Make sure you're running this from the project root")
        return

    print("🔍 Searching for suspicious posts...")
    print(f"   Post IDs: {', '.join(SUSPICIOUS_POST_IDS)}")
    print()

    all_posts = []
    files_by_creator = {}

    # Load all posts
    for json_file in data_dir.glob("*_posts_detailed.json"):
        creator_id = json_file.stem.replace('_posts_detailed', '')

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
                print(f"📄 Loaded {len(posts)} posts from {json_file.name}")

                files_by_creator[creator_id] = {
                    'file': json_file.name,
                    'posts': posts
                }

                all_posts.extend(posts)
        except Exception as e:
            print(f"❌ Error loading {json_file}: {e}")

    print(f"\n📊 Total posts loaded: {len(all_posts)}")
    print()

    # Check suspicious posts
    print("="*60)
    print("SUSPICIOUS POSTS ANALYSIS")
    print("="*60)

    for post_id in SUSPICIOUS_POST_IDS:
        print(f"\n🔎 Post ID: {post_id}")
        print("-" * 60)

        found = False
        for creator_id, data in files_by_creator.items():
            for post in data['posts']:
                if post.get('post_id') == post_id:
                    found = True
                    print(f"   ✓ Found in file: {data['file']}")
                    print(f"   📝 creator_id field: '{post.get('creator_id', 'MISSING')}'")
                    print(f"   📌 title: {post.get('title', 'No title')[:50]}")
                    print(f"   🔗 post_url: {post.get('post_url', 'No URL')}")

                    # Check if creator_id matches filename
                    if post.get('creator_id') == creator_id:
                        print(f"   ✅ creator_id MATCHES filename")
                    else:
                        print(f"   ⚠️  MISMATCH! creator_id='{post.get('creator_id')}' but file is '{creator_id}_posts_detailed.json'")

                    # Check URL for creator hint
                    url = post.get('post_url', '')
                    if '/posts/' in url:
                        url_creator = url.split('/')[3] if len(url.split('/')) > 3 else 'unknown'
                        print(f"   🌐 URL suggests creator: {url_creator}")

                    break

        if not found:
            print(f"   ❌ Post {post_id} NOT FOUND in any file!")

    # Statistics
    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)

    creator_counts = defaultdict(int)
    for post in all_posts:
        creator_id = post.get('creator_id', 'MISSING')
        creator_counts[creator_id] += 1

    for creator_id, count in sorted(creator_counts.items()):
        print(f"   {creator_id}: {count} posts")

    # Find mismatches
    print("\n" + "="*60)
    print("CHECKING ALL POSTS FOR MISMATCHES")
    print("="*60)

    mismatches = []
    for filename_creator, data in files_by_creator.items():
        for post in data['posts']:
            post_creator = post.get('creator_id', 'MISSING')
            if post_creator != filename_creator:
                mismatches.append({
                    'post_id': post.get('post_id'),
                    'file': data['file'],
                    'filename_creator': filename_creator,
                    'post_creator': post_creator,
                    'title': post.get('title', 'No title')[:50]
                })

    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} posts with mismatched creator_id!\n")
        for m in mismatches[:20]:  # Show first 20
            print(f"   Post {m['post_id']}: file says '{m['filename_creator']}' but post says '{m['post_creator']}'")
            print(f"      Title: {m['title']}")
            print()

        if len(mismatches) > 20:
            print(f"   ... and {len(mismatches) - 20} more")
    else:
        print("\n✅ No mismatches found! All posts have correct creator_id")

if __name__ == "__main__":
    diagnose_posts()
