#!/usr/bin/env python3
"""
Fix posts with incorrect creator_id
Moves posts between creator files when creator_id doesn't match filename
"""

import json
from pathlib import Path
from collections import defaultdict

def fix_mismatches():
    """Find and fix all posts with mismatched creator_id"""

    data_dir = Path("data/processed")

    if not data_dir.exists():
        print("❌ data/processed directory doesn't exist")
        return

    print("🔍 Loading all posts...")

    files_data = {}

    # Load all posts
    for json_file in data_dir.glob("*_posts_detailed.json"):
        filename_creator = json_file.stem.replace('_posts_detailed', '')

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
                files_data[filename_creator] = {
                    'file_path': json_file,
                    'posts': posts
                }
                print(f"   📄 Loaded {len(posts)} posts from {json_file.name}")
        except Exception as e:
            print(f"   ❌ Error loading {json_file}: {e}")

    print()

    # Find mismatches
    print("🔍 Checking for mismatches...")

    posts_to_move = defaultdict(list)  # {target_creator: [posts to add]}
    posts_to_remove = defaultdict(list)  # {source_creator: [post_ids to remove]}

    for filename_creator, data in files_data.items():
        for post in data['posts']:
            post_creator = post.get('creator_id', 'MISSING')

            if post_creator != filename_creator:
                post_id = post.get('post_id', 'unknown')
                title = post.get('title', 'No title')[:50]

                print(f"   ⚠️  Post {post_id}: '{title}'")
                print(f"       In file: {filename_creator}_posts_detailed.json")
                print(f"       Has creator_id: {post_creator}")
                print(f"       → Will move to {post_creator}_posts_detailed.json")
                print()

                posts_to_move[post_creator].append(post)
                posts_to_remove[filename_creator].append(post_id)

    if not posts_to_move:
        print("✅ No mismatches found! All posts are correctly assigned.")
        return

    # Ask for confirmation
    total_to_move = sum(len(posts) for posts in posts_to_move.values())
    print(f"\n📊 Summary: Found {total_to_move} posts to move")
    print("\nChanges to be made:")
    for target_creator, posts in posts_to_move.items():
        print(f"   → {len(posts)} posts will be moved to {target_creator}_posts_detailed.json")

    response = input("\n❓ Do you want to apply these fixes? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Cancelled. No changes made.")
        return

    # Create backups
    print("\n💾 Creating backups...")
    for filename_creator, data in files_data.items():
        backup_path = data['file_path'].with_suffix('.json.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data['posts'], f, indent=2, ensure_ascii=False)
        print(f"   ✓ Backed up {data['file_path'].name} → {backup_path.name}")

    # Remove posts from source files
    print("\n🗑️  Removing posts from incorrect files...")
    for source_creator, post_ids_to_remove in posts_to_remove.items():
        if source_creator in files_data:
            original_count = len(files_data[source_creator]['posts'])
            files_data[source_creator]['posts'] = [
                p for p in files_data[source_creator]['posts']
                if p.get('post_id') not in post_ids_to_remove
            ]
            new_count = len(files_data[source_creator]['posts'])
            print(f"   ✓ Removed {original_count - new_count} posts from {source_creator}")

    # Add posts to target files
    print("\n➕ Adding posts to correct files...")
    for target_creator, posts_to_add in posts_to_move.items():
        if target_creator not in files_data:
            print(f"   ⚠️  Target file {target_creator}_posts_detailed.json doesn't exist, creating new...")
            files_data[target_creator] = {
                'file_path': data_dir / f"{target_creator}_posts_detailed.json",
                'posts': []
            }

        files_data[target_creator]['posts'].extend(posts_to_add)
        print(f"   ✓ Added {len(posts_to_add)} posts to {target_creator}")

    # Save all modified files
    print("\n💾 Saving changes...")
    for creator, data in files_data.items():
        with open(data['file_path'], 'w', encoding='utf-8') as f:
            json.dump(data['posts'], f, indent=2, ensure_ascii=False)
        print(f"   ✓ Saved {data['file_path'].name} ({len(data['posts'])} posts)")

    print("\n✅ All fixes applied successfully!")
    print("\n📊 Final statistics:")
    for creator, data in sorted(files_data.items()):
        print(f"   {creator}: {len(data['posts'])} posts")

    print("\n💡 Tip: Backups were created with .backup extension")
    print("   If something went wrong, you can restore from backups")

if __name__ == "__main__":
    fix_mismatches()
