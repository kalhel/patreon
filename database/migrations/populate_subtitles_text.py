#!/usr/bin/env python3
"""
Populate subtitles_text column in posts table
==============================================

This script:
1. Scans all .vtt subtitle files in data/media/videos/
2. Extracts clean text from each subtitle file
3. Maps files to posts using post_id from filename
4. Updates subtitles_text column in PostgreSQL
5. Rebuilds search_vector for affected posts

Usage:
    python3 database/migrations/populate_subtitles_text.py

Requirements:
    - PostgreSQL database with posts table
    - .vtt files in data/media/videos/ subdirectories
    - sqlalchemy, psycopg2

Author: Javi + Claude
Date: 2025-11-09
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables"""
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not set in environment")

    # URL-encode password to handle special characters
    from urllib.parse import quote_plus
    password_encoded = quote_plus(db_password)

    return f"postgresql://{db_user}:{password_encoded}@{db_host}:{db_port}/{db_name}"


def parse_vtt_file(vtt_path: Path) -> str:
    """
    Parse a VTT subtitle file and extract clean text.

    Args:
        vtt_path: Path to .vtt file

    Returns:
        Cleaned subtitle text with timestamps removed
    """
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ⚠️  Error reading {vtt_path.name}: {e}")
        return ""

    text_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip VTT header
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue

        # Skip timestamp lines
        if '-->' in line:
            continue

        # Skip lines that look like cue identifiers (just numbers)
        if line.isdigit():
            continue

        # Remove inline timing tags like <00:00:02.399>
        line = re.sub(r'<\d+:\d+:\d+\.\d+>', '', line)

        # Remove XML-style tags like <c>
        line = re.sub(r'</?c>', '', line)

        # Clean up whitespace
        line = ' '.join(line.split())

        if line:
            text_lines.append(line)

    # Join with spaces and deduplicate consecutive identical segments
    full_text = ' '.join(text_lines)

    # Remove duplicate words that appear consecutively (VTT format quirk)
    # words = full_text.split()
    # deduplicated = [words[0]] if words else []
    # for i in range(1, len(words)):
    #     if words[i] != words[i-1]:
    #         deduplicated.append(words[i])
    # full_text = ' '.join(deduplicated)

    return full_text


def extract_post_id_from_filename(filename: str) -> str:
    """
    Extract post_id from VTT filename.

    Examples:
        110914542_yt00_en.vtt → 110914542
        113258529_00.vtt → 113258529

    Args:
        filename: Name of .vtt file

    Returns:
        post_id string or None if not found
    """
    # Pattern: {post_id}_{video_index}_{source}.vtt or {post_id}_{index}.vtt
    match = re.match(r'^(\d+)_', filename)
    if match:
        return match.group(1)
    return None


def find_vtt_files(base_path: Path) -> Dict[str, List[Path]]:
    """
    Find all .vtt files and group them by post_id.

    Args:
        base_path: Root path to search for .vtt files

    Returns:
        Dictionary mapping post_id to list of VTT file paths
    """
    vtt_files_by_post = {}

    for vtt_path in base_path.rglob('*.vtt'):
        post_id = extract_post_id_from_filename(vtt_path.name)

        if post_id:
            if post_id not in vtt_files_by_post:
                vtt_files_by_post[post_id] = []
            vtt_files_by_post[post_id].append(vtt_path)

    return vtt_files_by_post


def update_subtitles_in_database(engine, post_id: str, subtitles_text: str) -> bool:
    """
    Update subtitles_text and search_vector for a post.

    Args:
        engine: SQLAlchemy engine
        post_id: Post ID to update
        subtitles_text: Subtitle text to set

    Returns:
        True if update successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            # Update subtitles_text
            result = conn.execute(
                text("""
                    UPDATE posts
                    SET subtitles_text = :subtitles_text,
                        search_vector =
                            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                            setweight(to_tsvector('english', COALESCE(full_content, '')), 'B') ||
                            setweight(to_tsvector('english', COALESCE(array_to_string(patreon_tags, ' '), '')), 'C') ||
                            setweight(to_tsvector('english', COALESCE(comments_text, '')), 'D') ||
                            setweight(to_tsvector('english', COALESCE(:subtitles_text, '')), 'D')
                    WHERE post_id = :post_id
                      AND deleted_at IS NULL
                """),
                {
                    'post_id': post_id,
                    'subtitles_text': subtitles_text
                }
            )
            conn.commit()

            return result.rowcount > 0
    except Exception as e:
        print(f"  ⚠️  Database error for post {post_id}: {e}")
        return False


def main():
    """Main execution function"""
    print("=" * 80)
    print("Populating subtitles_text from .vtt files")
    print("=" * 80)
    print()

    # Find all VTT files
    base_path = Path('data/media/videos')

    if not base_path.exists():
        print(f"❌ Error: Directory not found: {base_path}")
        print("   Run this script from the project root directory.")
        sys.exit(1)

    print(f"📂 Scanning for .vtt files in: {base_path}")
    vtt_files_by_post = find_vtt_files(base_path)

    total_vtt_files = sum(len(files) for files in vtt_files_by_post.values())
    print(f"✅ Found {total_vtt_files} .vtt files for {len(vtt_files_by_post)} posts")
    print()

    if total_vtt_files == 0:
        print("⚠️  No .vtt files found. Exiting.")
        sys.exit(0)

    # Connect to database
    print("🔌 Connecting to PostgreSQL...")
    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM posts WHERE deleted_at IS NULL"))
            total_posts = result.scalar()
            print(f"✅ Connected. Database has {total_posts} active posts")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    print()
    print("=" * 80)
    print("Processing subtitle files")
    print("=" * 80)
    print()

    # Process each post
    updated_count = 0
    not_found_count = 0
    error_count = 0

    for post_id, vtt_files in sorted(vtt_files_by_post.items()):
        print(f"📝 Post {post_id}: {len(vtt_files)} subtitle file(s)")

        # Combine text from all VTT files for this post
        combined_text_parts = []

        for vtt_path in vtt_files:
            print(f"   → {vtt_path.name}")
            subtitle_text = parse_vtt_file(vtt_path)

            if subtitle_text:
                combined_text_parts.append(subtitle_text)
                print(f"     Extracted {len(subtitle_text)} characters")

        # Combine all subtitles for this post
        subtitles_text = ' '.join(combined_text_parts)

        if subtitles_text:
            # Update database
            if update_subtitles_in_database(engine, post_id, subtitles_text):
                updated_count += 1
                print(f"   ✅ Updated post {post_id} ({len(subtitles_text)} chars)")
            else:
                not_found_count += 1
                print(f"   ⚠️  Post {post_id} not found in database (may be deleted)")
        else:
            error_count += 1
            print(f"   ❌ No text extracted from subtitle files")

        print()

    # Summary
    print("=" * 80)
    print("✅ Processing Complete")
    print("=" * 80)
    print()
    print(f"Posts updated:    {updated_count}")
    print(f"Posts not found:  {not_found_count}")
    print(f"Errors:           {error_count}")
    print()

    # Verify in database
    print("📊 Verification:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE subtitles_text IS NOT NULL) as with_subtitles,
                COUNT(*) as total,
                ROUND(100.0 * COUNT(*) FILTER (WHERE subtitles_text IS NOT NULL) / COUNT(*), 1) as pct
            FROM posts
            WHERE deleted_at IS NULL
        """))
        row = result.fetchone()
        print(f"Posts with subtitles: {row.with_subtitles}/{row.total} ({row.pct}%)")

    print()
    print("🎉 Done! Subtitles are now searchable.")
    print()


if __name__ == '__main__':
    main()
