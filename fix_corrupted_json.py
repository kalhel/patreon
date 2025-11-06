#!/usr/bin/env python3
"""
Fix corrupted JSON file - specifically headonhistory_posts_detailed.json
The error "Extra data: line X" usually means multiple JSON objects without array wrapper
"""
import json
import sys
from pathlib import Path

def fix_json_file(filepath):
    """Try to fix corrupted JSON file"""
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False

    print(f"Analyzing {filepath.name}...")
    print(f"File size: {filepath.stat().st_size:,} bytes")

    # Read the raw content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Cannot read file: {e}")
        return False

    print(f"Content length: {len(content):,} characters")

    # Try different fixing strategies

    # Strategy 1: Check if it's multiple JSON arrays concatenated
    print("\n🔍 Checking for multiple JSON arrays...")
    array_count = content.count('][')
    if array_count > 0:
        print(f"   Found {array_count} array concatenations '][' ")
        print("   Attempting to fix by replacing '][' with ','")

        fixed_content = content.replace('][', ',')

        try:
            posts = json.loads(fixed_content)
            print(f"   ✅ Successfully parsed {len(posts)} posts!")

            # Create backup
            backup_path = filepath.with_suffix('.json.backup')
            print(f"\n💾 Creating backup: {backup_path.name}")
            filepath.rename(backup_path)

            # Write fixed file
            print(f"💾 Writing fixed file: {filepath.name}")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)

            print(f"\n✅ SUCCESS! File fixed with {len(posts)} posts")
            print(f"   Original backed up to: {backup_path.name}")
            return True

        except json.JSONDecodeError as e:
            print(f"   ❌ Still invalid after fix: {e}")

    # Strategy 2: Try to find where the valid JSON ends
    print("\n🔍 Trying to find valid JSON portion...")
    try:
        # Try to decode incrementally to find where it breaks
        decoder = json.JSONDecoder()
        posts, idx = decoder.raw_decode(content)

        if idx < len(content):
            extra_data = content[idx:idx+200]
            print(f"   Found valid JSON up to position {idx:,}")
            print(f"   Extra data starts with: {repr(extra_data[:100])}")

            # Check if the extra data is another array
            remaining = content[idx:].strip()
            if remaining.startswith('['):
                print(f"   Extra data looks like another array!")

                try:
                    extra_posts, _ = decoder.raw_decode(remaining)
                    print(f"   Found {len(extra_posts)} additional posts in extra data")

                    # Merge the arrays
                    all_posts = posts + extra_posts
                    print(f"   Total posts after merge: {len(all_posts)}")

                    # Create backup
                    backup_path = filepath.with_suffix('.json.backup')
                    print(f"\n💾 Creating backup: {backup_path.name}")
                    filepath.rename(backup_path)

                    # Write fixed file
                    print(f"💾 Writing fixed file: {filepath.name}")
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(all_posts, f, indent=2, ensure_ascii=False)

                    print(f"\n✅ SUCCESS! File fixed with {len(all_posts)} posts")
                    print(f"   Original backed up to: {backup_path.name}")
                    return True

                except Exception as e2:
                    print(f"   ❌ Cannot parse extra array: {e2}")

            # If we can't merge, at least save what we have
            print(f"\n⚠️  Can save {len(posts)} valid posts, but will lose extra data")
            response = input("   Save valid portion? (y/n): ")
            if response.lower() == 'y':
                backup_path = filepath.with_suffix('.json.backup')
                print(f"💾 Creating backup: {backup_path.name}")
                filepath.rename(backup_path)

                print(f"💾 Writing fixed file: {filepath.name}")
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(posts, f, indent=2, ensure_ascii=False)

                print(f"\n✅ Saved {len(posts)} valid posts")
                print(f"   Original backed up to: {backup_path.name}")
                return True

    except json.JSONDecodeError as e:
        print(f"   ❌ Cannot find valid JSON: {e}")

    print(f"\n❌ Unable to automatically fix this file")
    print(f"   You may need to:")
    print(f"   1. Re-run the scraper to regenerate this file")
    print(f"   2. Manually inspect and edit the file")
    print(f"   3. Check for write errors during scraping")

    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_corrupted_json.py <path_to_json_file>")
        print("\nOr auto-fix headonhistory:")
        print("  python fix_corrupted_json.py data/processed/headonhistory_posts_detailed.json")
        sys.exit(1)

    filepath = sys.argv[1]
    print("="*70)
    print("JSON FILE REPAIR TOOL")
    print("="*70)
    print()

    success = fix_json_file(filepath)

    if success:
        print("\n" + "="*70)
        print("✅ REPAIR COMPLETE!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Restart your Flask server")
        print("  2. Reload the page in your browser")
        print("  3. You should now see all creators including headonhistory")
    else:
        print("\n" + "="*70)
        print("❌ REPAIR FAILED")
        print("="*70)
        print("\nRecommended action:")
        print("  Re-run the scraper for this creator to regenerate the file")

if __name__ == "__main__":
    main()
