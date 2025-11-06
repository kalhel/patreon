#!/usr/bin/env python3
"""
Diagnostic script to find why headonhistory is missing
"""
import json
from pathlib import Path

print("="*70)
print("HEADONHISTORY DIAGNOSTIC SCRIPT")
print("="*70)

# Check data directories
raw_dir = Path("data/raw")
processed_dir = Path("data/processed")

print("\n1. CHECKING DATA DIRECTORIES:")
print(f"   Raw dir exists: {raw_dir.exists()} - {raw_dir.absolute()}")
print(f"   Processed dir exists: {processed_dir.exists()} - {processed_dir.absolute()}")

# Find all post JSON files
all_json_files = []
if raw_dir.exists():
    all_json_files.extend(list(raw_dir.glob("*_posts.json")))
if processed_dir.exists():
    all_json_files.extend(list(processed_dir.glob("*_posts_detailed.json")))

print(f"\n2. FOUND {len(all_json_files)} POST JSON FILES:")
for f in all_json_files:
    print(f"   - {f}")

# Check each file for headonhistory
print(f"\n3. CHECKING EACH FILE FOR HEADONHISTORY POSTS:")
headonhistory_posts = []
all_posts_by_creator = {}

for json_file in all_json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        print(f"\n   File: {json_file.name}")
        print(f"   Total posts: {len(posts)}")

        # Count by creator
        creators_in_file = {}
        for post in posts:
            creator_id = post.get('creator_id', 'unknown')
            if creator_id not in creators_in_file:
                creators_in_file[creator_id] = 0
            creators_in_file[creator_id] += 1

            # Track all posts by creator
            if creator_id not in all_posts_by_creator:
                all_posts_by_creator[creator_id] = []
            all_posts_by_creator[creator_id].append(post)

            # Track headonhistory specifically
            if creator_id == 'headonhistory':
                headonhistory_posts.append(post)

        print(f"   Creators in this file:")
        for cid, count in creators_in_file.items():
            indicator = " 👈 FOUND!" if cid == 'headonhistory' else ""
            print(f"     - {cid}: {count} posts{indicator}")

    except Exception as e:
        print(f"   ❌ Error reading {json_file}: {e}")

print("\n" + "="*70)
print("4. FINAL SUMMARY:")
print("="*70)
print(f"\nAll creators found across all files:")
for creator_id in sorted(all_posts_by_creator.keys()):
    count = len(all_posts_by_creator[creator_id])
    indicator = " ✅ GOOD!" if creator_id == 'headonhistory' else ""
    print(f"  {creator_id}: {count} posts{indicator}")

if 'headonhistory' in all_posts_by_creator:
    print(f"\n✅ SUCCESS: Found {len(all_posts_by_creator['headonhistory'])} headonhistory posts!")
    print(f"\n   Sample post IDs:")
    for post in all_posts_by_creator['headonhistory'][:5]:
        print(f"     - {post.get('post_id')}: {post.get('title', 'Untitled')[:50]}")
else:
    print("\n❌ PROBLEM: NO headonhistory posts found in any file!")
    print("\n   Possible causes:")
    print("   1. The JSON files don't contain headonhistory posts")
    print("   2. The creator_id field is different (check for typos, spaces, case)")
    print("   3. The data files are old or corrupted")

    print(f"\n   Other creators found: {list(all_posts_by_creator.keys())}")

print("\n" + "="*70)
print("5. CREATOR ID VARIATIONS CHECK:")
print("="*70)
print("\nLooking for similar creator IDs (case-insensitive):")
for creator_id in sorted(all_posts_by_creator.keys()):
    if 'head' in creator_id.lower() or 'history' in creator_id.lower():
        print(f"  - '{creator_id}' (length: {len(creator_id)})")
        print(f"    First chars: {repr(creator_id[:20])}")

print("\n" + "="*70)
