#!/usr/bin/env python3
"""
Cleanup script to remove Mux thumbnail URLs from videos field in existing posts.

Mux thumbnails are preview images (not videos) with URLs like:
stream.mux.com/[id]/medium.mp4?token=...&time=6.0

This script:
1. Finds all posts with Mux thumbnail URLs in videos field
2. Removes those thumbnails
3. Updates the database
"""

import psycopg2
import json
import os
from dotenv import load_dotenv

def is_mux_thumbnail(url):
    """Check if URL is a Mux thumbnail (has 'time=' parameter)"""
    return 'stream.mux.com' in url.lower() and 'time=' in url.lower()

def main():
    load_dotenv()

    print("=" * 80)
    print("Cleanup: Remove Mux Thumbnails from videos field")
    print("=" * 80)
    print()

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'alejandria'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

    cursor = conn.cursor()

    # Find all posts with videos
    cursor.execute("""
        SELECT post_id, title, videos
        FROM posts
        WHERE videos IS NOT NULL
        AND array_length(videos, 1) > 0
    """)

    posts_to_update = []
    total_thumbnails_found = 0

    print("Scanning posts for Mux thumbnails...")
    print()

    for post_id, title, videos_json in cursor.fetchall():
        # Parse videos
        if isinstance(videos_json, str):
            videos = json.loads(videos_json)
        else:
            videos = videos_json

        # Filter out thumbnails
        clean_videos = [v for v in videos if not is_mux_thumbnail(v)]

        # If any were removed, mark for update
        if len(clean_videos) < len(videos):
            thumbnails_removed = len(videos) - len(clean_videos)
            total_thumbnails_found += thumbnails_removed

            posts_to_update.append({
                'post_id': post_id,
                'title': title[:60],
                'old_count': len(videos),
                'new_count': len(clean_videos),
                'clean_videos': clean_videos
            })

            print(f"Post {post_id}: {title[:60]}")
            print(f"  Videos before: {len(videos)}")
            print(f"  Videos after:  {len(clean_videos)}")
            print(f"  Thumbnails removed: {thumbnails_removed}")
            print()

    print("-" * 80)
    print(f"Found {len(posts_to_update)} posts with Mux thumbnails")
    print(f"Total thumbnails to remove: {total_thumbnails_found}")
    print("-" * 80)
    print()

    if not posts_to_update:
        print("✓ No Mux thumbnails found. Database is clean!")
        conn.close()
        return

    # Ask for confirmation
    response = input(f"Update {len(posts_to_update)} posts? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Aborted. No changes made.")
        conn.close()
        return

    # Update posts
    print()
    print("Updating posts...")
    updated_count = 0

    for post in posts_to_update:
        try:
            cursor.execute("""
                UPDATE posts
                SET videos = %s,
                    updated_at = NOW()
                WHERE post_id = %s
            """, (post['clean_videos'], post['post_id']))

            updated_count += 1

            if updated_count % 10 == 0:
                print(f"  Updated {updated_count}/{len(posts_to_update)} posts...")

        except Exception as e:
            print(f"  ✗ Error updating post {post['post_id']}: {e}")

    # Commit changes
    conn.commit()

    print()
    print("=" * 80)
    print(f"✓ Successfully updated {updated_count} posts")
    print(f"✓ Removed {total_thumbnails_found} Mux thumbnail URLs")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
