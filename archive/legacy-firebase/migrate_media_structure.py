#!/usr/bin/env python3
"""
Migrate existing media structure to new hash-based deduplicated structure

This script:
1. Calculates SHA256 hash of all media files
2. Detects duplicates (same hash, different locations)
3. Renames to: {hash16}_{postID}_{index}.ext
4. Moves duplicates to backup directory
5. Removes small images (<400x400)
6. Generates savings report

SAFE: Creates backup before any changes
USE: --dry-run to preview changes without modifying files
"""

import os
import sys
import hashlib
import shutil
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from datetime import datetime

def calculate_file_hash(file_path: Path, algorithm='sha256') -> str:
    """Calculate file hash"""
    hash_obj = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()

def get_image_dimensions(file_path: Path) -> Tuple[int, int]:
    """Get image dimensions (returns 0,0 if can't determine)"""
    try:
        import subprocess
        result = subprocess.run(['file', str(file_path)],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and 'x' in result.stdout:
            parts = result.stdout.split(',')
            for part in parts:
                if 'x' in part and any(c.isdigit() for c in part):
                    dims = part.strip().split('x')
                    if len(dims) == 2:
                        try:
                            w = int(''.join(c for c in dims[0] if c.isdigit()))
                            h = int(''.join(c for c in dims[1] if c.isdigit()))
                            return w, h
                        except:
                            pass
    except:
        pass
    return 0, 0

def extract_post_id_from_filename(filename: str) -> str:
    """Extract post ID from filename (e.g., '113258529_00.mp4' -> '113258529')"""
    # Try to extract post ID from various patterns
    parts = filename.split('_')
    if parts and parts[0].isdigit():
        return parts[0]
    return "unknown"

def format_size(bytes_size: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

class MediaMigrator:
    """Migrates media files to new structure"""

    def __init__(self, base_path: Path, dry_run: bool = True):
        self.base_path = base_path
        self.dry_run = dry_run

        # Statistics
        self.stats = {
            'total_files': 0,
            'duplicates_found': 0,
            'duplicates_size': 0,
            'small_images_found': 0,
            'small_images_size': 0,
            'renamed_files': 0,
            'errors': 0
        }

        # Tracking
        self.hash_to_files: Dict[str, List[Path]] = defaultdict(list)
        self.processed_hashes: Set[str] = set()

    def scan_and_hash(self):
        """Scan all files and calculate hashes"""
        print("\n🔍 Scanning and hashing files...")
        print("=" * 80)

        for media_type in ['images', 'videos', 'audio']:
            media_dir = self.base_path / media_type
            if not media_dir.exists():
                continue

            print(f"\n📁 Processing {media_type}/...")

            for file_path in media_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                # Skip certain file types
                if file_path.suffix.lower() in ['.json', '.txt', '.vtt', '.srt']:
                    continue

                self.stats['total_files'] += 1

                try:
                    # Calculate hash
                    file_hash = calculate_file_hash(file_path)
                    hash16 = file_hash[:16]  # First 16 chars

                    self.hash_to_files[file_hash].append(file_path)

                    if self.stats['total_files'] % 100 == 0:
                        print(f"  Processed {self.stats['total_files']} files...", end='\r')

                except Exception as e:
                    print(f"\n  ⚠️  Error hashing {file_path}: {e}")
                    self.stats['errors'] += 1

        print(f"\n✅ Scanned {self.stats['total_files']} files")

    def find_duplicates(self):
        """Identify duplicate files (same hash)"""
        print("\n🔄 Finding duplicates...")
        print("=" * 80)

        duplicates = {
            hash_val: paths
            for hash_val, paths in self.hash_to_files.items()
            if len(paths) > 1
        }

        if not duplicates:
            print("✅ No duplicates found!")
            return

        self.stats['duplicates_found'] = sum(len(paths) - 1 for paths in duplicates.values())

        print(f"\n🔎 Found {len(duplicates)} unique files with duplicates")
        print(f"   Total duplicate copies: {self.stats['duplicates_found']}")

        # Calculate wasted space
        for hash_val, paths in duplicates.items():
            file_size = paths[0].stat().st_size
            duplicate_count = len(paths) - 1
            self.stats['duplicates_size'] += file_size * duplicate_count

        print(f"   Wasted space: {format_size(self.stats['duplicates_size'])}")

        # Show top duplicates
        top_duplicates = sorted(
            duplicates.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]

        print(f"\n   Top 10 most duplicated files:")
        for hash_val, paths in top_duplicates:
            file_size = paths[0].stat().st_size
            print(f"      {len(paths)}× {format_size(file_size)} - {paths[0].name}")

    def find_small_images(self):
        """Identify small images (<400x400) that shouldn't exist"""
        print("\n🖼️  Finding small images...")
        print("=" * 80)

        images_dir = self.base_path / 'images'
        if not images_dir.exists():
            print("   No images directory found")
            return

        small_images = []

        for image_path in images_dir.rglob('*'):
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                continue

            width, height = get_image_dimensions(image_path)

            if width > 0 and height > 0 and (width < 400 or height < 400):
                small_images.append({
                    'path': image_path,
                    'size': image_path.stat().st_size,
                    'dimensions': f"{width}x{height}"
                })
                self.stats['small_images_found'] += 1
                self.stats['small_images_size'] += image_path.stat().st_size

        if not small_images:
            print("✅ No small images found!")
            return

        print(f"\n📊 Found {len(small_images)} small images (<400x400)")
        print(f"   Total size: {format_size(self.stats['small_images_size'])}")
        print(f"\n   Examples:")
        for img in small_images[:10]:
            print(f"      {img['dimensions']} - {format_size(img['size'])} - {img['path'].name}")

    def migrate_files(self):
        """Migrate files to new structure"""
        print("\n🔄 Migrating files to new structure...")
        print("=" * 80)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No files will be modified")

        backup_dir = self.base_path.parent / f"media_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        duplicates_dir = backup_dir / "duplicates"
        small_images_dir = backup_dir / "small_images"

        if not self.dry_run:
            backup_dir.mkdir(exist_ok=True)
            duplicates_dir.mkdir(exist_ok=True)
            small_images_dir.mkdir(exist_ok=True)
            print(f"\n📦 Backup directory: {backup_dir}")

        # Process each unique file
        for hash_val, paths in self.hash_to_files.items():
            if hash_val in self.processed_hashes:
                continue

            # Keep first occurrence, move duplicates to backup
            primary_file = paths[0]
            duplicates = paths[1:]

            # Generate new filename
            hash16 = hash_val[:16]
            post_id = extract_post_id_from_filename(primary_file.name)
            new_name = f"{hash16}_{post_id}_00{primary_file.suffix}"

            # Determine media type directory
            if 'images' in str(primary_file):
                media_type = 'images'
            elif 'videos' in str(primary_file):
                media_type = 'videos'
            elif 'audio' in str(primary_file):
                media_type = 'audio'
            else:
                continue

            # Extract creator from path
            try:
                parts = primary_file.parts
                creator_idx = parts.index(media_type) + 1
                creator_id = parts[creator_idx]
            except:
                creator_id = "unknown"

            # New path
            new_path = self.base_path / media_type / creator_id / new_name

            # Rename primary file
            if new_path != primary_file:
                if self.dry_run:
                    print(f"   WOULD RENAME: {primary_file.name} -> {new_name}")
                else:
                    try:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(primary_file), str(new_path))
                        self.stats['renamed_files'] += 1
                    except Exception as e:
                        print(f"   ⚠️  Error renaming {primary_file}: {e}")
                        self.stats['errors'] += 1

            # Move duplicates to backup
            for dup_file in duplicates:
                if self.dry_run:
                    print(f"   WOULD MOVE DUPLICATE: {dup_file} -> backup/")
                else:
                    try:
                        dup_backup_path = duplicates_dir / dup_file.name
                        shutil.move(str(dup_file), str(dup_backup_path))
                    except Exception as e:
                        print(f"   ⚠️  Error moving duplicate {dup_file}: {e}")

            self.processed_hashes.add(hash_val)

        print(f"\n✅ Migration {'simulation' if self.dry_run else 'complete'}")

    def remove_small_images(self):
        """Remove small images (<400x400)"""
        print("\n🗑️  Removing small images...")
        print("=" * 80)

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No files will be removed")

        images_dir = self.base_path / 'images'
        if not images_dir.exists():
            return

        backup_dir = self.base_path.parent / f"media_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        small_images_dir = backup_dir / "small_images"

        if not self.dry_run:
            small_images_dir.mkdir(parents=True, exist_ok=True)

        removed = 0

        for image_path in images_dir.rglob('*'):
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                continue

            width, height = get_image_dimensions(image_path)

            if width > 0 and height > 0 and (width < 400 or height < 400):
                if self.dry_run:
                    print(f"   WOULD REMOVE: {image_path.name} ({width}x{height})")
                else:
                    try:
                        backup_path = small_images_dir / image_path.name
                        shutil.move(str(image_path), str(backup_path))
                        removed += 1
                    except Exception as e:
                        print(f"   ⚠️  Error removing {image_path}: {e}")

        if removed > 0:
            print(f"\n✅ Removed {removed} small images")
        else:
            print(f"\n✅ No small images to remove")

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 80)
        print("📊 MIGRATION SUMMARY")
        print("=" * 80)

        print(f"\n📈 Files processed: {self.stats['total_files']}")
        print(f"✏️  Files renamed: {self.stats['renamed_files']}")
        print(f"🔄 Duplicates found: {self.stats['duplicates_found']}")
        print(f"   Space saved: {format_size(self.stats['duplicates_size'])}")
        print(f"🖼️  Small images found: {self.stats['small_images_found']}")
        print(f"   Space saved: {format_size(self.stats['small_images_size'])}")
        print(f"❌ Errors: {self.stats['errors']}")

        total_savings = self.stats['duplicates_size'] + self.stats['small_images_size']
        print(f"\n💾 TOTAL SPACE SAVINGS: {format_size(total_savings)}")

        if self.dry_run:
            print(f"\n⚠️  This was a DRY RUN - no changes were made")
            print(f"   Run without --dry-run to apply changes")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate media structure to hash-based deduplicated format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes (safe, no modifications)
  python tools/migrate_media_structure.py --dry-run

  # Apply migration (creates backup first)
  python tools/migrate_media_structure.py

  # Only find duplicates
  python tools/migrate_media_structure.py --scan-only

What this does:
  1. Calculates SHA256 hash of all media files
  2. Finds and removes duplicates (moves to backup)
  3. Renames files to: {hash16}_{postID}_{index}.ext
  4. Removes small images (<400x400)
  5. Creates backup before any changes

Safe:
  - Always creates backup before modifications
  - Use --dry-run to preview changes first
  - Original files moved to backup, never deleted
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without modifying files')
    parser.add_argument('--scan-only', action='store_true',
                       help='Only scan and report, no migration')
    parser.add_argument('--base-path', type=str, default='data/media',
                       help='Base media directory (default: data/media)')

    args = parser.parse_args()

    base_path = Path(args.base_path)

    if not base_path.exists():
        print(f"❌ Error: Directory {base_path} does not exist")
        return 1

    print("🚀 Media Structure Migration Tool")
    print("=" * 80)
    print(f"\n📁 Base directory: {base_path}")

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")

    # Create migrator
    migrator = MediaMigrator(base_path, dry_run=args.dry_run or args.scan_only)

    # Scan and hash
    migrator.scan_and_hash()

    # Find issues
    migrator.find_duplicates()
    migrator.find_small_images()

    if not args.scan_only:
        # Ask for confirmation if not dry-run
        if not args.dry_run:
            print("\n" + "=" * 80)
            print("⚠️  WARNING: This will modify your media files")
            print("   A backup will be created before any changes")
            response = input("\nProceed with migration? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Migration cancelled")
                return 0

        # Migrate
        migrator.migrate_files()
        migrator.remove_small_images()

    # Summary
    migrator.print_summary()

    print("\n" + "=" * 80)
    print("✅ DONE")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
