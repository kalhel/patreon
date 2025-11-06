#!/usr/bin/env python3
"""
Find all posts that contain YouTube videos
This helps identify which posts need thumbnail re-processing
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from firebase_tracker import FirebaseTracker, load_firebase_config
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def find_youtube_posts(tracker: FirebaseTracker, creator_id: str = None):
    """
    Find all posts that contain YouTube videos

    Args:
        tracker: Firebase tracker instance
        creator_id: Optional creator filter

    Returns:
        Dict mapping creator_id to list of post IDs with YouTube videos
    """
    youtube_posts = {}
    total_posts = 0
    total_with_youtube = 0

    # Get all posts
    all_posts = tracker.get_all_posts()

    if not all_posts:
        return youtube_posts, total_posts, total_with_youtube

    # Filter by creator if specified
    if creator_id:
        all_posts = {
            post_id: post for post_id, post in all_posts.items()
            if post.get('creator_id') == creator_id
        }

    # Group by creator
    for post_id, post in all_posts.items():
        total_posts += 1
        creator = post.get('creator_id', 'unknown')
        content_blocks = post.get('content_blocks', [])

        # Check if any content block is a YouTube embed
        has_youtube = any(
            block.get('type') == 'youtube_embed'
            for block in content_blocks
        )

        if has_youtube:
            total_with_youtube += 1
            if creator not in youtube_posts:
                youtube_posts[creator] = []
            youtube_posts[creator].append(post_id)

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

    args = parser.parse_args()

    # Load Firebase config
    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    logger.info("🔍 Scanning for posts with YouTube videos...\n")

    # Find YouTube posts
    youtube_posts, total_posts, total_with_youtube = find_youtube_posts(
        tracker,
        creator_id=args.creator
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
