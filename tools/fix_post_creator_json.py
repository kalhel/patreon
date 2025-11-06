#!/usr/bin/env python3
"""
Fix creator_id for post 128693945 in local JSON files
Changes creator_id from 'astrobymax' to 'headonhistory'
"""

import json
from pathlib import Path

def find_and_fix_post(post_id: str, correct_creator_id: str):
    """Find and fix post in JSON files"""

    # Directories to search
    search_dirs = [
        Path("data/raw"),
        Path("data/processed")
    ]

    found = False
    fixed_files = []

    for search_dir in search_dirs:
        if not search_dir.exists():
            print(f"⚠️  Directory not found: {search_dir}")
            continue

        print(f"🔍 Searching in {search_dir}...")

        # Find all JSON files
        json_files = list(search_dir.glob("*_posts*.json"))

        for json_file in json_files:
            try:
                # Load posts
                with open(json_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)

                # Find and fix the post
                modified = False
                for post in posts:
                    if post.get('post_id') == post_id:
                        found = True
                        current_creator = post.get('creator_id', 'unknown')

                        print(f"\n✓ Found post {post_id} in {json_file.name}")
                        print(f"  Current creator_id: {current_creator}")

                        # Check metadata
                        metadata = post.get('post_metadata', {})
                        if metadata:
                            metadata_creator = metadata.get('creator_name', 'N/A')
                            print(f"  Metadata creator_name: {metadata_creator}")

                        # Fix if needed
                        if current_creator != correct_creator_id:
                            post['creator_id'] = correct_creator_id
                            modified = True
                            print(f"  🔧 Updated creator_id to: {correct_creator_id}")
                        else:
                            print(f"  ✓ Already correct")

                # Save if modified
                if modified:
                    # Create backup
                    backup_path = json_file.with_suffix('.json.bak')
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(posts, f, indent=2, ensure_ascii=False)
                    print(f"  💾 Backup saved: {backup_path.name}")

                    # Save updated file
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(posts, f, indent=2, ensure_ascii=False)
                    print(f"  ✓ Saved: {json_file.name}")
                    fixed_files.append(json_file)

            except Exception as e:
                print(f"⚠️  Error processing {json_file.name}: {e}")

    return found, fixed_files

def main():
    print("="*60)
    print("🔧 Fix Post Creator ID")
    print("="*60)
    print()

    post_id = '128693945'
    correct_creator_id = 'headonhistory'

    print(f"Target Post ID: {post_id}")
    print(f"Correct creator_id: {correct_creator_id}")
    print()

    found, fixed_files = find_and_fix_post(post_id, correct_creator_id)

    print()
    print("="*60)
    if found:
        if fixed_files:
            print(f"✅ Success! Fixed {len(fixed_files)} file(s)")
            for f in fixed_files:
                print(f"   - {f}")
            print()
            print("🎉 Done! Reload the Flask web app to see the changes:")
            print("   python3 web/viewer.py")
        else:
            print("✓ Post found and already has correct creator_id")
    else:
        print(f"❌ Post {post_id} not found in any JSON file")
        print()
        print("💡 Make sure you have posts in:")
        print("   - data/raw/")
        print("   - data/processed/")
    print("="*60)

if __name__ == "__main__":
    main()
