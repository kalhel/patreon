#!/usr/bin/env python3
"""
Find all posts that contain YouTube videos
This helps identify which posts need thumbnail re-processing
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def load_posts_from_json(data_dir: Path, creator_id: str = None) -> Dict:
    """
    Load posts from JSON files in data/processed/

    Args:
        data_dir: Path to data directory
        creator_id: Optional creator filter

    Returns:
        Dict of all posts
    """
    processed_dir = data_dir / "processed"

    if not processed_dir.exists():
        logger.error(f"❌ Directory not found: {processed_dir}")
        return {}

    all_posts = {}

    # Find all JSON files
    if creator_id:
        json_files = [processed_dir / f"{creator_id}_posts_detailed.json"]
    else:
        json_files = list(processed_dir.glob("*_posts_detailed.json"))

    for json_file in json_files:
        if not json_file.exists():
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)

            for post in posts:
                post_id = post.get('post_id')
                if post_id:
                    all_posts[post_id] = post

        except Exception as e:
            logger.warning(f"⚠️  Error reading {json_file}: {e}")

    return all_posts


def find_youtube_posts(creator_id: str = None, debug: bool = False) -> Tuple[Dict, int, int]:
    """
    Find all posts that contain YouTube videos

    Args:
        creator_id: Optional creator filter
        debug: Print debug information about block types

    Returns:
        Tuple of (youtube_posts dict, total_posts, total_with_youtube)
    """
    youtube_posts = {}
    total_posts = 0
    total_with_youtube = 0

    # Get project root (parent of tools/)
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    # Load posts from JSON files
    all_posts = load_posts_from_json(data_dir, creator_id)

    if not all_posts:
        return youtube_posts, total_posts, total_with_youtube

    # Debug: collect all block types
    if debug:
        all_types = set()
        video_types = set()

    # Group by creator and find YouTube videos
    for post_id, post in all_posts.items():
        total_posts += 1
        creator = post.get('creator_id', 'unknown')
        content_blocks = post.get('content_blocks', [])

        if debug:
            for block in content_blocks:
                block_type = block.get('type', 'unknown')
                all_types.add(block_type)
                # Check if it might be a video
                if 'video' in block_type.lower() or 'youtube' in block_type.lower() or 'embed' in block_type.lower():
                    video_types.add(block_type)
                    if block_type not in ['youtube_embed']:
                        logger.info(f"  Found video type: {block_type} in post {post_id}")

        # Check if any content block is a YouTube/video embed
        # Look for: youtube_embed, video, iframe with youtube URL
        has_youtube = False
        for block in content_blocks:
            block_type = block.get('type', '')

            if block_type == 'youtube_embed':
                has_youtube = True
                break

            # Check for video blocks
            if block_type == 'video':
                url = block.get('url', '').lower()
                if 'youtube' in url or 'youtu.be' in url:
                    has_youtube = True
                    break

            # Check for iframes with YouTube
            if block_type == 'iframe':
                url = block.get('url', '').lower()
                if 'youtube' in url or 'youtu.be' in url:
                    has_youtube = True
                    break

        if has_youtube:
            total_with_youtube += 1
            if creator not in youtube_posts:
                youtube_posts[creator] = []
            youtube_posts[creator].append(post_id)

    if debug:
        logger.info(f"\n🔍 Debug - All block types found: {sorted(all_types)}")
        logger.info(f"🎬 Debug - Video-related types: {sorted(video_types)}\n")

    return youtube_posts, total_posts, total_with_youtube


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Find all posts with YouTube videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find all posts with YouTube videos
  python tools/find_youtube_posts.py

  # Find YouTube posts for specific creator
  python tools/find_youtube_posts.py --creator headonhistory

  # Save post IDs to file for batch processing
  python tools/find_youtube_posts.py --output youtube_posts.txt

  # Generate re-scrape command
  python tools/find_youtube_posts.py --generate-command
        """
    )

    parser.add_argument('--creator', type=str,
                        help='Only find posts for this creator')
    parser.add_argument('--output', type=str,
                        help='Save post IDs to file (one per line)')
    parser.add_argument('--generate-command', action='store_true',
                        help='Generate bash command to re-scrape all YouTube posts')
    parser.add_argument('--debug', action='store_true',
                        help='Show debug information about block types found')

    args = parser.parse_args()

    logger.info("🔍 Scanning for posts with YouTube videos...\n")

    # Find YouTube posts
    youtube_posts, total_posts, total_with_youtube = find_youtube_posts(
        creator_id=args.creator,
        debug=args.debug
    )

    # Print summary
    logger.info(f"📊 Summary:")
    logger.info(f"   Total posts scanned: {total_posts}")
    logger.info(f"   Posts with YouTube: {total_with_youtube}")
    logger.info(f"   Percentage: {(total_with_youtube/total_posts*100):.1f}%\n")

    if not youtube_posts:
        logger.info("✅ No posts with YouTube videos found")
        return

    # Print by creator
    logger.info("📹 Posts with YouTube videos:\n")
    all_post_ids = []

    for creator, post_ids in youtube_posts.items():
        logger.info(f"   {creator}: {len(post_ids)} posts")
        all_post_ids.extend(post_ids)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            for post_id in all_post_ids:
                f.write(f"{post_id}\n")
        logger.info(f"\n💾 Saved {len(all_post_ids)} post IDs to: {output_path}")

    # Generate command if requested
    if args.generate_command:
        logger.info("\n🔧 To re-scrape all YouTube posts, run these commands:\n")
        for creator, post_ids in youtube_posts.items():
            logger.info(f"# Re-scrape {creator} ({len(post_ids)} posts)")
            for post_id in post_ids:
                logger.info(f"python src/phase2_detail_extractor.py --post {post_id} --headless")
            logger.info("")

    # Print first 10 post IDs as example
    if not args.generate_command and len(all_post_ids) > 0:
        logger.info(f"\n📝 Example post IDs (first 10):")
        for post_id in all_post_ids[:10]:
            logger.info(f"   {post_id}")
        if len(all_post_ids) > 10:
            logger.info(f"   ... and {len(all_post_ids) - 10} more")


if __name__ == '__main__':
    main()
