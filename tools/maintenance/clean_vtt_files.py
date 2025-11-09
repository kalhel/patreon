#!/usr/bin/env python3
"""
Clean VTT Subtitle Files
Removes alignment parameters (align:start, position:0%, etc.) from VTT files
that break centered subtitle display in the web viewer.
"""

import re
from pathlib import Path
import sys


def clean_vtt_file(vtt_path: Path) -> bool:
    """
    Clean alignment parameters from a VTT subtitle file.

    Args:
        vtt_path: Path to VTT file to clean

    Returns:
        bool: True if cleaned successfully
    """
    try:
        # Read the file
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Remove alignment parameters from timestamp lines
        # Pattern: "00:00:00.000 --> 00:00:00.000 align:start position:0%"
        # We want: "00:00:00.000 --> 00:00:00.000"

        # Remove align:start, align:end, align:middle, etc.
        content = re.sub(r'\s+align:\w+', '', content)

        # Remove position:N%
        content = re.sub(r'\s+position:\d+%', '', content)

        # Remove line:N%
        content = re.sub(r'\s+line:\d+%', '', content)

        # Remove size:N%
        content = re.sub(r'\s+size:\d+%', '', content)

        # Only write if content changed
        if content != original_content:
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Cleaned: {vtt_path}")
            return True
        else:
            print(f"  - Already clean: {vtt_path}")
            return False

    except Exception as e:
        print(f"  ✗ Error cleaning {vtt_path}: {e}")
        return False


def main():
    """Find and clean all VTT files in data/media/videos"""

    # Find data/media directory
    script_dir = Path(__file__).parent
    media_dir = script_dir / "data" / "media" / "videos"

    if not media_dir.exists():
        print(f"❌ Media directory not found: {media_dir}")
        print("This script should be run from the project root directory.")
        sys.exit(1)

    # Find all VTT files
    vtt_files = list(media_dir.rglob("*.vtt"))

    if not vtt_files:
        print(f"No VTT files found in {media_dir}")
        return

    print(f"Found {len(vtt_files)} VTT files to process\n")

    cleaned_count = 0
    already_clean_count = 0
    error_count = 0

    for vtt_file in vtt_files:
        result = clean_vtt_file(vtt_file)
        if result:
            cleaned_count += 1
        elif result is False:
            already_clean_count += 1
        else:
            error_count += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total files: {len(vtt_files)}")
    print(f"Cleaned: {cleaned_count}")
    print(f"Already clean: {already_clean_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
