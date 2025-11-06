#!/usr/bin/env python3
"""
Reset/clean processed data for a specific creator
This allows you to re-process a creator from scratch if data is corrupted
"""
import sys
import argparse
from pathlib import Path
import shutil
from datetime import datetime

# Add src to path for Firebase access
sys.path.insert(0, 'src')

def reset_creator_files(creator_id, backup=True):
    """Remove processed files for a creator"""
    print(f"\n{'='*70}")
    print(f"RESETTING CREATOR: {creator_id}")
    print(f"{'='*70}\n")

    data_dir = Path("data")
    processed_dir = data_dir / "processed"
    raw_dir = data_dir / "raw"

    files_to_reset = []

    # Find all files for this creator
    if processed_dir.exists():
        files_to_reset.extend(processed_dir.glob(f"{creator_id}_*"))

    if raw_dir.exists():
        files_to_reset.extend(raw_dir.glob(f"{creator_id}_*"))

    if not files_to_reset:
        print(f"⚠️  No files found for creator '{creator_id}'")
        print(f"\nChecked directories:")
        print(f"  - {processed_dir}")
        print(f"  - {raw_dir}")
        return False

    print(f"Found {len(files_to_reset)} files to reset:")
    for f in files_to_reset:
        size_mb = f.stat().st_size / (1024*1024)
        print(f"  📄 {f.relative_to(data_dir)} ({size_mb:.2f} MB)")

    if backup:
        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = data_dir / "backups" / f"{creator_id}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Creating backup in: {backup_dir.relative_to(data_dir)}")

        for f in files_to_reset:
            dest = backup_dir / f.name
            shutil.copy2(f, dest)
            print(f"  ✓ Backed up: {f.name}")

    # Remove the files
    print(f"\n🗑️  Removing files...")
    for f in files_to_reset:
        f.unlink()
        print(f"  ✓ Deleted: {f.name}")

    print(f"\n✅ Successfully reset {len(files_to_reset)} files for '{creator_id}'")

    if backup:
        print(f"   Backup saved to: {backup_dir.relative_to(data_dir)}")

    return True

def reset_firebase(creator_id):
    """Reset Firebase status for a creator"""
    try:
        from firebase_tracker import load_firebase_config, FirebaseTracker

        print(f"\n🔄 Resetting Firebase status for '{creator_id}'...")

        database_url, database_secret = load_firebase_config()
        tracker = FirebaseTracker(database_url, database_secret)

        # Get all posts for this creator
        all_posts = tracker.get_all_posts()
        creator_posts = [
            (post_id, post)
            for post_id, post in all_posts.items()
            if post.get('creator_id') == creator_id
        ]

        if not creator_posts:
            print(f"   ⚠️  No posts found in Firebase for '{creator_id}'")
            return False

        print(f"   Found {len(creator_posts)} posts in Firebase")

        # Reset details_extracted status for all posts
        reset_count = 0
        for post_id, post in creator_posts:
            if post.get('status', {}).get('details_extracted', False):
                tracker.mark_details_extracted(post_id, success=False, error=None)
                reset_count += 1

        print(f"   ✓ Reset {reset_count} posts to pending state")

        # Update stats
        tracker.update_creator_stats(creator_id)

        print(f"✅ Firebase reset complete for '{creator_id}'")
        return True

    except ImportError:
        print("⚠️  Firebase not available (firebase_tracker not found)")
        return False
    except Exception as e:
        print(f"❌ Error resetting Firebase: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Reset processed data for a specific creator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset headonhistory with backup
  python reset_creator.py headonhistory

  # Reset without creating backup
  python reset_creator.py headonhistory --no-backup

  # Reset and also clear Firebase status
  python reset_creator.py headonhistory --firebase

  # Just list files without deleting
  python reset_creator.py headonhistory --dry-run

After resetting, re-run the scraper to regenerate clean data:
  python daily_scrape_v2.sh
        """
    )

    parser.add_argument('creator_id', help='Creator ID to reset (e.g., headonhistory)')
    parser.add_argument('--no-backup', action='store_true', help='Delete without creating backup')
    parser.add_argument('--firebase', action='store_true', help='Also reset Firebase status')
    parser.add_argument('--dry-run', action='store_true', help='List files without deleting')

    args = parser.parse_args()

    print("="*70)
    print("CREATOR DATA RESET TOOL")
    print("="*70)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be deleted\n")
        data_dir = Path("data")
        processed_dir = data_dir / "processed"
        raw_dir = data_dir / "raw"

        files_found = []
        if processed_dir.exists():
            files_found.extend(processed_dir.glob(f"{args.creator_id}_*"))
        if raw_dir.exists():
            files_found.extend(raw_dir.glob(f"{args.creator_id}_*"))

        if files_found:
            print(f"Would reset {len(files_found)} files:")
            for f in files_found:
                size_mb = f.stat().st_size / (1024*1024)
                print(f"  📄 {f.relative_to(data_dir)} ({size_mb:.2f} MB)")
        else:
            print(f"No files found for '{args.creator_id}'")

        return

    # Confirm action
    print(f"\n⚠️  WARNING: This will reset all processed data for '{args.creator_id}'")
    if not args.no_backup:
        print("   A backup will be created before deletion.")
    else:
        print("   NO BACKUP will be created!")

    response = input("\nContinue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled by user")
        return

    # Reset files
    success = reset_creator_files(args.creator_id, backup=not args.no_backup)

    if not success:
        print("\n❌ No files were reset")
        return

    # Reset Firebase if requested
    if args.firebase:
        reset_firebase(args.creator_id)

    print("\n" + "="*70)
    print("✅ RESET COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print(f"  1. Re-run the scraper for '{args.creator_id}':")
    print(f"     ./daily_scrape_v2.sh")
    print(f"  2. Wait for processing to complete")
    print(f"  3. Restart Flask server: python web/viewer.py")
    print(f"  4. Check that '{args.creator_id}' appears correctly\n")

if __name__ == "__main__":
    main()
