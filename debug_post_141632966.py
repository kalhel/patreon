#!/usr/bin/env python3
"""
Debug script to investigate post 141632966 video issue
User reports: downloaded video is different (appears to be an ad instead of real video)
Original post has a Vimeo embed
"""

import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    load_dotenv()

    print("=" * 80)
    print("DEBUG: Post 141632966 Video Investigation")
    print("=" * 80)
    print()

    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'alejandria'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT post_id, title, videos, video_local_paths
        FROM posts
        WHERE post_id = '141632966'
    """)

    row = cursor.fetchone()

    if not row:
        print("✗ Post not found in database")
        conn.close()
        return

    post_id, title, videos, video_local = row

    print(f"Post ID: {post_id}")
    print(f"Title: {title}")
    print()

    print("-" * 80)
    print("VIDEOS CAPTURED (URLs in database)")
    print("-" * 80)
    if videos and len(videos) > 0:
        print(f"Count: {len(videos)}")
        for i, v in enumerate(videos, 1):
            print(f"\n{i}. {v}")

            # Identify video source
            if 'vimeo.com' in v.lower():
                print("   Type: Vimeo")
            elif 'youtube.com' in v.lower() or 'youtu.be' in v.lower():
                print("   Type: YouTube")
            elif 'stream.mux.com' in v.lower():
                print("   Type: Mux")
            else:
                print("   Type: Unknown")
    else:
        print("(none)")
    print()

    print("-" * 80)
    print("VIDEOS DOWNLOADED (local files)")
    print("-" * 80)
    if video_local and len(video_local) > 0:
        print(f"Count: {len(video_local)}")
        for i, p in enumerate(video_local, 1):
            print(f"\n{i}. {p}")

            # Check file info
            full_path = Path('data/media') / p
            if full_path.exists():
                size = full_path.stat().st_size
                print(f"   Size: {size:,} bytes ({size/1024/1024:.2f} MB)")

                # Check if it's suspiciously small (likely an ad/preview)
                if size < 5 * 1024 * 1024:  # Less than 5 MB
                    print(f"   ⚠️  WARNING: File is very small (< 5 MB) - likely a preview/ad, not full video")
                elif size < 20 * 1024 * 1024:  # Less than 20 MB
                    print(f"   ⚠️  WARNING: File seems small - may be low quality or partial download")
                else:
                    print(f"   ✓ File size seems reasonable for a video")
            else:
                print(f"   ✗ FILE NOT FOUND at {full_path}")
    else:
        print("(none)")
    print()

    print("-" * 80)
    print("DIAGNOSIS")
    print("-" * 80)

    if not videos or len(videos) == 0:
        print("⚠️  No video URLs were captured during scraping")
        print("   This may indicate scraper didn't detect the Vimeo embed")
    elif not video_local or len(video_local) == 0:
        print("⚠️  Video URL was captured but NOT downloaded")
        print("   Check media_downloader logs for errors")
    elif len(videos) != len(video_local):
        print(f"⚠️  URL count ({len(videos)}) != downloaded count ({len(video_local)})")
        print("   Some videos failed to download")
    else:
        print("✓ URL count matches downloaded count")
        print()
        print("Next steps:")
        print("1. Check if downloaded file size is reasonable (see above)")
        print("2. Play the downloaded video to verify it's correct content")
        print("3. If it's wrong, the issue is likely:")
        print("   - Scraper captured wrong URL (check 'videos' field above)")
        print("   - yt-dlp downloaded wrong content from the URL")

    conn.close()

if __name__ == '__main__':
    main()
