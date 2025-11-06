#!/usr/bin/env python3
"""
Debug script to check subtitle files and video configuration
"""
from pathlib import Path
import json

def main():
    # Check for VTT files
    media_dir = Path('data/media')

    if not media_dir.exists():
        print("❌ data/media directory not found!")
        print("\nChecking if any media files exist elsewhere...")

        # Try to find VTT files anywhere
        vtt_files_any = list(Path('.').rglob('*.vtt'))
        if vtt_files_any:
            print(f"\n⚠️  Found {len(vtt_files_any)} .vtt files in other locations:")
            for f in vtt_files_any[:5]:
                print(f"  {f}")
        else:
            print("\n❌ No .vtt files found anywhere in the project!")
        return

    print("🔍 Searching for .vtt subtitle files...\n")

    vtt_files = list(media_dir.rglob('*.vtt'))

    if not vtt_files:
        print("❌ No .vtt files found in media directory!")
        print("\nThis means subtitles haven't been downloaded yet.")
        print("You need to run the scraper to download videos with subtitles.")
        return

    print(f"✅ Found {len(vtt_files)} subtitle files:\n")

    for vtt_file in vtt_files:
        relative_path = vtt_file.relative_to(media_dir)
        file_size = vtt_file.stat().st_size
        print(f"  📝 {relative_path}")
        print(f"     Size: {file_size} bytes")

        # Check if the file has content
        if file_size == 0:
            print(f"     ⚠️  WARNING: File is empty!")
        else:
            # Read first few lines
            try:
                with open(vtt_file, 'r', encoding='utf-8') as f:
                    first_lines = f.read(200)
                    if 'WEBVTT' in first_lines:
                        print(f"     ✅ Valid WebVTT format")
                    else:
                        print(f"     ⚠️  May not be valid WebVTT format")
            except Exception as e:
                print(f"     ❌ Error reading file: {e}")
        print()

    # Now check if any processed posts have video_subtitles_relative
    print("\n" + "="*60)
    print("🔍 Checking processed posts for subtitle references...\n")

    data_dir = Path('data/processed')
    if not data_dir.exists():
        print("❌ No processed data directory found")
        return

    posts_with_subs = []

    for json_file in data_dir.glob('*_posts_detailed.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)

                for post in posts:
                    if post.get('video_subtitles_relative'):
                        posts_with_subs.append({
                            'post_id': post.get('post_id'),
                            'title': post.get('title', 'No title')[:50],
                            'subtitles': post.get('video_subtitles_relative'),
                            'videos': post.get('video_local_paths', [])
                        })
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    if posts_with_subs:
        print(f"✅ Found {len(posts_with_subs)} posts with subtitle references:\n")
        for post in posts_with_subs:
            print(f"Post ID: {post['post_id']}")
            print(f"Title: {post['title']}")
            print(f"Videos: {post['videos']}")
            print(f"Subtitles: {post['subtitles']}")
            print()
    else:
        print("❌ No posts found with video_subtitles_relative field!")
        print("\nThis means the posts need to be reprocessed to extract subtitles.")

    print("\n" + "="*60)
    print("💡 RECOMMENDATIONS:")
    print("="*60)

    if not vtt_files:
        print("1. Run the phase2 extractor to download videos with subtitles")
        print("   Example: python3 src/phase2_detail_extractor.py --post POST_ID")
    elif not posts_with_subs:
        print("1. The VTT files exist but posts don't reference them")
        print("2. Reprocess the posts to link the subtitles")
    else:
        print("1. ✅ Subtitles are downloaded and referenced")
        print("2. Make sure you restarted the Flask server (python3 web/viewer.py)")
        print("3. Clear your browser cache (Ctrl+Shift+R)")
        print(f"4. Try viewing post: http://localhost:5000/post/{posts_with_subs[0]['post_id']}")

if __name__ == '__main__':
    main()
