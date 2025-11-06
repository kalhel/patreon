#!/usr/bin/env python3
"""
Re-scrape posts with YouTube videos to get better thumbnails
Uses the new intelligent thumbnail processor
"""

import sys
from pathlib import Path

# Add src and tools directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from firebase_tracker import FirebaseTracker, load_firebase_config
from phase2_detail_extractor import extract_post_details, authenticate
import json
import logging
from find_youtube_posts import find_youtube_posts

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from credentials.json and creators.json"""
    config_dir = Path(__file__).parent.parent / "config"

    # Load credentials
    credentials_path = config_dir / "credentials.json"
    with open(credentials_path) as f:
        config = json.load(f)

    # Load creators from separate file
    creators_path = config_dir / "creators.json"
    if creators_path.exists():
        with open(creators_path) as f:
            creators_data = json.load(f)
            config['patreon']['creators'] = creators_data.get('creators', [])

    return config


def rescrape_post(scraper, tracker: FirebaseTracker, post_id: str):
    """
    Re-scrape a single post to update YouTube thumbnails

    Args:
        scraper: Patreon scraper instance
        tracker: Firebase tracker
        post_id: Post ID to re-scrape

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get existing post data from Firebase
        post = tracker.get_post(post_id)
        if not post:
            logger.error(f"❌ Post {post_id} not found in Firebase")
            return False

        creator_id = post.get('creator_id')

        if not creator_id:
            logger.error(f"❌ Post {post_id} has no creator_id")
            return False

        logger.info(f"🔄 Re-scraping post {post_id} ({creator_id})...")

        # Use the same extract_post_details function from phase2
        # This will re-scrape and save to JSON with updated thumbnails
        success = extract_post_details(scraper, tracker, post, save_to_json=True)

        if success:
            logger.info(f"✅ Successfully re-scraped post {post_id}")
            return True
        else:
            logger.error(f"❌ Failed to re-scrape post {post_id}")
            return False

    except Exception as e:
        logger.error(f"❌ Error re-scraping post {post_id}: {e}")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Re-scrape posts with YouTube videos to update thumbnails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-scrape all posts with YouTube videos
  python tools/rescrape_youtube_posts.py --all

  # Re-scrape YouTube posts for specific creator
  python tools/rescrape_youtube_posts.py --creator headonhistory

  # Re-scrape specific posts from file
  python tools/rescrape_youtube_posts.py --file youtube_posts.txt

  # Limit number of posts to process
  python tools/rescrape_youtube_posts.py --all --limit 10

  # Dry run (show what would be done)
  python tools/rescrape_youtube_posts.py --all --dry-run
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Re-scrape all posts with YouTube videos')
    parser.add_argument('--creator', type=str,
                        help='Only process posts from this creator')
    parser.add_argument('--file', type=str,
                        help='Read post IDs from file (one per line)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of posts to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without actually doing it')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                        help='Show browser window')

    args = parser.parse_args()

    if not any([args.all, args.creator, args.file]):
        parser.print_help()
        return

    # Load config
    config = load_config()
    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    # Find posts to re-scrape
    post_ids_to_process = []

    if args.file:
        # Load from file
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"❌ File not found: {args.file}")
            return

        with open(file_path) as f:
            post_ids_to_process = [line.strip() for line in f if line.strip()]

        logger.info(f"📂 Loaded {len(post_ids_to_process)} post IDs from {args.file}")

    else:
        # Find YouTube posts
        logger.info("🔍 Finding posts with YouTube videos...\n")
        youtube_posts, total_posts, total_with_youtube = find_youtube_posts(
            tracker,
            creator_id=args.creator
        )

        # Flatten post IDs
        for creator, post_ids in youtube_posts.items():
            post_ids_to_process.extend(post_ids)

        logger.info(f"\n📊 Found {len(post_ids_to_process)} posts with YouTube videos")

    # Apply limit
    if args.limit:
        post_ids_to_process = post_ids_to_process[:args.limit]
        logger.info(f"🔢 Limited to {len(post_ids_to_process)} posts")

    if not post_ids_to_process:
        logger.info("✅ No posts to process")
        return

    # Dry run
    if args.dry_run:
        logger.info(f"\n🏃 DRY RUN - Would re-scrape {len(post_ids_to_process)} posts:")
        for i, post_id in enumerate(post_ids_to_process[:10], 1):
            logger.info(f"   {i}. {post_id}")
        if len(post_ids_to_process) > 10:
            logger.info(f"   ... and {len(post_ids_to_process) - 10} more")
        return

    # Authenticate using phase2's authenticate function
    logger.info("\n🔐 Authenticating with Patreon...")
    auth = authenticate(config, headless=args.headless)

    if not auth:
        logger.error("❌ Failed to authenticate")
        return

    logger.info("✅ Authentication successful")

    # Create scraper
    from patreon_scraper_v2 import PatreonScraperV2
    scraper = PatreonScraperV2(auth)

    # Process posts
    logger.info(f"\n🚀 Re-scraping {len(post_ids_to_process)} posts...\n")

    success_count = 0
    failed_count = 0

    try:
        for i, post_id in enumerate(post_ids_to_process, 1):
            logger.info(f"\n[{i}/{len(post_ids_to_process)}] Processing post {post_id}...")

            if rescrape_post(scraper, tracker, post_id):
                success_count += 1
            else:
                failed_count += 1

        # Summary
        logger.info("\n" + "="*60)
        logger.info("📊 Re-scraping Summary:")
        logger.info(f"   ✅ Successful: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📝 Total: {len(post_ids_to_process)}")
        logger.info("="*60)

    finally:
        logger.info("\n🎉 Done! Press ENTER to close browser...")
        input()
        auth.close()


if __name__ == '__main__':
    main()
