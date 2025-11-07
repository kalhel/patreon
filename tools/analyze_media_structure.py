#!/usr/bin/env python3
"""
Analyze data/media/ structure to understand current storage and identify issues

This script analyzes:
- Directory structure and file organization
- File counts by type and creator
- File sizes and disk usage
- Duplicate files (same name or size)
- Small images (likely avatars/icons)
- Naming patterns

Run this and share the output to help design the optimal storage structure.
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import json

def format_size(bytes_size: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def get_image_dimensions(file_path: Path) -> Tuple[int, int]:
    """Get image dimensions without PIL (returns 0,0 if can't determine)"""
    try:
        # Try to use 'file' command to get basic info
        import subprocess
        result = subprocess.run(['file', str(file_path)],
                              capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and 'x' in result.stdout:
            # Try to extract dimensions from output
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

def analyze_media_directory(base_path: Path = Path("data/media")) -> Dict:
    """Analyze media directory structure"""

    if not base_path.exists():
        return {
            "error": f"Directory {base_path} does not exist",
            "exists": False
        }

    print(f"🔍 Analyzing {base_path}...\n")

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_type": defaultdict(lambda: {"count": 0, "size": 0, "files": []}),
        "by_creator": defaultdict(lambda: {"count": 0, "size": 0, "by_type": {}}),
        "small_images": [],  # < 400x400
        "large_files": [],   # > 100 MB
        "duplicates_by_size": defaultdict(list),
        "duplicates_by_name": defaultdict(list),
        "naming_patterns": defaultdict(int),
        "directory_structure": {}
    }

    # Walk through all files
    for root, dirs, files in os.walk(base_path):
        rel_root = Path(root).relative_to(base_path)

        for file in files:
            file_path = Path(root) / file

            try:
                file_size = file_path.stat().st_size
                stats["total_files"] += 1
                stats["total_size"] += file_size

                # Get file type
                ext = file_path.suffix.lower()
                media_type = None
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    media_type = 'images'
                elif ext in ['.mp4', '.webm', '.mov', '.m4v', '.mkv']:
                    media_type = 'videos'
                elif ext in ['.mp3', '.m4a', '.wav', '.ogg']:
                    media_type = 'audio'
                elif ext in ['.vtt', '.srt']:
                    media_type = 'subtitles'
                else:
                    media_type = 'other'

                # Track by type
                stats["by_type"][media_type]["count"] += 1
                stats["by_type"][media_type]["size"] += file_size
                stats["by_type"][media_type]["files"].append({
                    "name": file,
                    "size": file_size,
                    "path": str(rel_root)
                })

                # Extract creator from path (assuming structure: media_type/creator_id/...)
                parts = str(rel_root).split(os.sep)
                if len(parts) >= 2:
                    creator = parts[1]
                    stats["by_creator"][creator]["count"] += 1
                    stats["by_creator"][creator]["size"] += file_size
                    if media_type not in stats["by_creator"][creator]["by_type"]:
                        stats["by_creator"][creator]["by_type"][media_type] = {"count": 0, "size": 0}
                    stats["by_creator"][creator]["by_type"][media_type]["count"] += 1
                    stats["by_creator"][creator]["by_type"][media_type]["size"] += file_size

                # Check for small images (likely avatars/icons)
                if media_type == 'images':
                    width, height = get_image_dimensions(file_path)
                    if width > 0 and height > 0 and (width < 400 or height < 400):
                        stats["small_images"].append({
                            "name": file,
                            "size": file_size,
                            "dimensions": f"{width}x{height}",
                            "path": str(rel_root)
                        })

                # Check for large files
                if file_size > 100 * 1024 * 1024:  # > 100 MB
                    stats["large_files"].append({
                        "name": file,
                        "size": file_size,
                        "type": media_type,
                        "path": str(rel_root)
                    })

                # Track duplicates by size
                stats["duplicates_by_size"][file_size].append({
                    "name": file,
                    "path": str(file_path.relative_to(base_path))
                })

                # Track duplicates by name
                stats["duplicates_by_name"][file].append({
                    "size": file_size,
                    "path": str(file_path.relative_to(base_path))
                })

                # Analyze naming patterns
                if '_' in file:
                    parts = file.split('_')
                    if len(parts) >= 2:
                        pattern = f"{parts[0]}_*"  # e.g., "12345_*"
                        stats["naming_patterns"][pattern] += 1

            except Exception as e:
                print(f"⚠️  Error processing {file_path}: {e}")
                continue

    # Find actual duplicates (more than one file with same size)
    actual_duplicates_by_size = {
        size: files for size, files in stats["duplicates_by_size"].items()
        if len(files) > 1
    }
    stats["duplicates_by_size"] = dict(list(actual_duplicates_by_size.items())[:20])  # Top 20

    actual_duplicates_by_name = {
        name: files for name, files in stats["duplicates_by_name"].items()
        if len(files) > 1
    }
    stats["duplicates_by_name"] = dict(list(actual_duplicates_by_name.items())[:20])  # Top 20

    # Keep only top examples for file lists
    for media_type in stats["by_type"]:
        files = stats["by_type"][media_type]["files"]
        stats["by_type"][media_type]["example_files"] = files[:5]  # Keep 5 examples
        del stats["by_type"][media_type]["files"]

    # Sort and limit
    stats["small_images"] = sorted(stats["small_images"], key=lambda x: x["size"])[:20]
    stats["large_files"] = sorted(stats["large_files"], key=lambda x: x["size"], reverse=True)[:10]
    stats["naming_patterns"] = dict(sorted(stats["naming_patterns"].items(),
                                          key=lambda x: x[1], reverse=True)[:15])

    return stats

def print_analysis(stats: Dict):
    """Print analysis results"""

    if "error" in stats:
        print(f"❌ {stats['error']}")
        return

    print("=" * 80)
    print("📊 MEDIA STORAGE ANALYSIS")
    print("=" * 80)
    print()

    # Overall stats
    print("📈 OVERALL STATISTICS")
    print(f"   Total files: {stats['total_files']:,}")
    print(f"   Total size:  {format_size(stats['total_size'])}")
    print()

    # By media type
    print("📁 BY MEDIA TYPE")
    for media_type, data in sorted(stats["by_type"].items(),
                                   key=lambda x: x[1]["size"], reverse=True):
        print(f"   {media_type.upper()}:")
        print(f"      Files: {data['count']:,}")
        print(f"      Size:  {format_size(data['size'])}")
        if "example_files" in data and data["example_files"]:
            print(f"      Examples:")
            for f in data["example_files"][:3]:
                print(f"         - {f['name']} ({format_size(f['size'])}) in {f['path']}")
        print()

    # By creator
    print("👤 BY CREATOR")
    for creator, data in sorted(stats["by_creator"].items(),
                               key=lambda x: x[1]["size"], reverse=True):
        print(f"   {creator}:")
        print(f"      Total files: {data['count']:,}")
        print(f"      Total size:  {format_size(data['size'])}")
        if data["by_type"]:
            print(f"      Breakdown:")
            for media_type, type_data in sorted(data["by_type"].items()):
                print(f"         {media_type}: {type_data['count']} files ({format_size(type_data['size'])})")
        print()

    # Small images
    if stats["small_images"]:
        print("🔍 SMALL IMAGES (likely avatars/icons - should NOT download)")
        print(f"   Found {len(stats['small_images'])} images < 400x400px")
        print(f"   Examples:")
        for img in stats["small_images"][:10]:
            print(f"      - {img['name']} ({img['dimensions']}, {format_size(img['size'])}) in {img['path']}")
        print()

    # Large files
    if stats["large_files"]:
        print("💾 LARGEST FILES")
        for f in stats["large_files"][:10]:
            print(f"   - {f['name']} ({format_size(f['size'])}) [{f['type']}] in {f['path']}")
        print()

    # Duplicates by size
    if stats["duplicates_by_size"]:
        print("🔄 POTENTIAL DUPLICATES (same file size)")
        print(f"   Found {len(stats['duplicates_by_size'])} size groups with multiple files")
        print(f"   Examples:")
        for size, files in list(stats["duplicates_by_size"].items())[:5]:
            print(f"      Size {format_size(size)}: {len(files)} files")
            for f in files[:3]:
                print(f"         - {f['path']}")
        print()

    # Duplicates by name
    if stats["duplicates_by_name"]:
        print("📝 DUPLICATE NAMES (same filename in different locations)")
        print(f"   Found {len(stats['duplicates_by_name'])} duplicate filenames")
        print(f"   Examples:")
        for name, files in list(stats["duplicates_by_name"].items())[:5]:
            print(f"      {name}: {len(files)} locations")
            for f in files[:3]:
                print(f"         - {f['path']} ({format_size(f['size'])})")
        print()

    # Naming patterns
    if stats["naming_patterns"]:
        print("🏷️  NAMING PATTERNS")
        print(f"   Top patterns:")
        for pattern, count in list(stats["naming_patterns"].items())[:10]:
            print(f"      {pattern}: {count} files")
        print()

    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("💡 RECOMMENDATIONS:")
    print("   1. Review small images - likely avatars/icons that shouldn't be downloaded")
    print("   2. Check duplicates - may indicate reprocessing without deduplication")
    print("   3. Consider organizing by date if many files per creator")
    print("   4. Implement SHA256 hash deduplication to prevent duplicates")
    print()

def main():
    """Run analysis"""
    print("🚀 Media Structure Analysis Tool")
    print()

    base_path = Path("data/media")
    stats = analyze_media_directory(base_path)
    print_analysis(stats)

    # Save to JSON for detailed inspection
    output_file = Path("data/media_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"📄 Detailed analysis saved to: {output_file}")
    print()
    print("📋 Share this output to help design the optimal storage structure!")

if __name__ == "__main__":
    main()
