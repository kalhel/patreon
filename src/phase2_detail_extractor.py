#!/usr/bin/env python3
"""
Phase 2: Post Detail Extractor
Extracts full details from posts tracked in Firebase
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from firebase_tracker import FirebaseTracker, load_firebase_config
from media_downloader import MediaDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase2_detail_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

media_downloader = MediaDownloader()


def load_config():
    """Load configuration from credentials.json"""
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        return json.load(f)


def authenticate(config, headless=True):
    """
    Authenticate with Patreon

    Args:
        config: Configuration dictionary
        headless: Run browser in headless mode

    Returns:
        PatreonAuthSelenium instance
    """
    email = config['patreon']['email']
    password = config['patreon']['password']

    auth = PatreonAuthSelenium(email, password, headless=headless)

    # Try to load existing cookies
    if auth.load_cookies():
        logger.info("📂 Loaded existing cookies")
        if auth.is_authenticated():
            logger.info("✅ Already authenticated!")
            return auth
        else:
            logger.warning("⚠️  Cookies expired, need to login again")

    # Login
    logger.info("🔐 Logging in to Patreon...")
    if not auth.login(manual_mode=False):
        logger.error("❌ Login failed!")
        return None

    auth.save_cookies()
    logger.info("✅ Authentication successful!")

    return auth


def extract_post_details(
    scraper: PatreonScraperV2,
    tracker: FirebaseTracker,
    post: Dict,
    save_to_json: bool = True
) -> bool:
    """
    Extract full details for a single post

    Args:
        scraper: PatreonScraperV2 instance
        tracker: FirebaseTracker instance
        post: Post record from Firebase
        save_to_json: Whether to save details to JSON file

    Returns:
        True if successful
    """
    post_id = post['post_id']
    post_url = post['post_url']
    creator_id = post['creator_id']

    logger.info(f"\n📄 Extracting details for post {post_id}")
    logger.info(f"   URL: {post_url}")

    # Increment attempt counter
    tracker.increment_attempt(post_id)

    try:
        # Scrape full post details
        post_detail = scraper.scrape_post_detail(post_url, post_id=post.get('post_id'))

        if not post_detail:
            error_msg = "Failed to extract post details"
            logger.error(f"   ❌ {error_msg}")
            tracker.mark_details_extracted(post_id, success=False, error=error_msg)
            return False

        # Merge with existing data
        full_post_data = {
            **post,  # Existing Firebase data
            **post_detail  # New scraped details
        }

        # Ensure Patreon session cookies are available for authenticated media URLs
        media_downloader.sync_cookies_from_driver(scraper.driver)

        # Download media immediately so local assets are linked to the post data
        download_result = media_downloader.download_all_from_post(full_post_data, creator_id)
        full_post_data['downloaded_media'] = download_result
        if download_result.get('videos_relative'):
            full_post_data['video_local_paths'] = download_result['videos_relative']
        if download_result.get('video_subtitles_relative'):
            full_post_data['video_subtitles_relative'] = download_result['video_subtitles_relative']
        if download_result.get('audios_relative'):
            full_post_data['audio_local_paths'] = download_result['audios_relative']
        if download_result.get('images_relative'):
            full_post_data['image_local_paths'] = download_result['images_relative']

        # Save to JSON file if requested
        if save_to_json:
            output_dir = Path("data/processed")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save to creator-specific file
            output_file = output_dir / f"{creator_id}_posts_detailed.json"

            # Load existing data
            existing_posts = []
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_posts = json.load(f)

            # Update or append
            post_exists = False
            for i, p in enumerate(existing_posts):
                if p.get('post_id') == post_id:
                    existing_posts[i] = full_post_data
                    post_exists = True
                    break

            if not post_exists:
                existing_posts.append(full_post_data)

            # Save updated data
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(existing_posts, f, indent=2, ensure_ascii=False)

            logger.info(f"   💾 Saved to {output_file}")

        # Mark as extracted in Firebase
        tracker.mark_details_extracted(post_id, success=True)

        logger.info(f"   ✅ Successfully extracted details for post {post_id}")
        logger.info(f"      - Title: {post_detail.get('title', 'N/A')}")
        logger.info(f"      - Images: {len(post_detail.get('images', []))}")
        logger.info(f"      - Videos: {len(post_detail.get('videos', []))}")
        logger.info(f"      - Audios: {len(post_detail.get('audios', []))}")
        logger.info(f"      - Tags: {len(post_detail.get('patreon_tags', []))}")

        return True

    except Exception as e:
        logger.exception(f"   ❌ Error extracting post {post_id}")
        tracker.mark_details_extracted(post_id, success=False, error=str(e))
        return False


def extract_all_pending(
    scraper: PatreonScraperV2,
    tracker: FirebaseTracker,
    creator_id: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, int]:
    """
    Extract details for all posts needing extraction

    Args:
        scraper: PatreonScraperV2 instance
        tracker: FirebaseTracker instance
        creator_id: Optional filter by creator
        limit: Optional limit on posts to process

    Returns:
        Dictionary with success/failure counts
    """
    # Get posts needing details
    posts_needing_details = tracker.get_posts_needing_details(creator_id)

    if not posts_needing_details:
        logger.info("✅ No posts need detail extraction!")
        return {"success": 0, "failed": 0, "total": 0}

    # Sort by post_id descending (higher = more recent)
    posts_needing_details = sorted(posts_needing_details, key=lambda x: int(x.get('post_id', 0)), reverse=True)

    # Apply limit if specified
    if limit:
        posts_needing_details = posts_needing_details[:limit]

    logger.info(f"\n{'='*60}")
    logger.info(f"📥 Found {len(posts_needing_details)} posts needing detail extraction")
    logger.info(f"{'='*60}\n")

    success_count = 0
    failed_count = 0

    for i, post in enumerate(posts_needing_details, 1):
        logger.info(f"\n[{i}/{len(posts_needing_details)}] Processing post...")

        success = extract_post_details(scraper, tracker, post)

        if success:
            success_count += 1
        else:
            failed_count += 1

        # Update creator stats after each post
        tracker.update_creator_stats(post['creator_id'])

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 PHASE 2 BATCH COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed:     {failed_count}")
    logger.info(f"Total:      {len(posts_needing_details)}")
    logger.info(f"{'='*60}\n")

    return {
        "success": success_count,
        "failed": failed_count,
        "total": len(posts_needing_details)
    }


def extract_single_post(
    scraper: PatreonScraperV2,
    tracker: FirebaseTracker,
    post_id: str
) -> bool:
    """
    Extract details for a specific post

    Args:
        scraper: PatreonScraperV2 instance
        tracker: FirebaseTracker instance
        post_id: Post ID to extract

    Returns:
        True if successful
    """
    # Get post from Firebase
    post = tracker.get_post(post_id)

    if not post:
        logger.error(f"❌ Post {post_id} not found in Firebase")
        return False

    # Check if already extracted
    if post.get('status', {}).get('details_extracted', False):
        logger.warning(f"⚠️  Post {post_id} already has details extracted")
        logger.info("Extracting anyway...")

    # Extract details
    success = extract_post_details(scraper, tracker, post)

    if success:
        tracker.update_creator_stats(post['creator_id'])

    return success


def main():
    parser = argparse.ArgumentParser(
        description='Phase 2: Extract Patreon Post Details',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract details for all pending posts
  python phase2_detail_extractor.py --all

  # Extract details for all pending posts (limit 5)
  python phase2_detail_extractor.py --all --limit 5

  # Extract details for single creator
  python phase2_detail_extractor.py --creator headonhistory

  # Extract details for specific post
  python phase2_detail_extractor.py --post 142518617

  # Show Firebase summary
  python phase2_detail_extractor.py --summary
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Extract details for all pending posts')
    parser.add_argument('--creator', type=str,
                        help='Extract details for single creator')
    parser.add_argument('--post', type=str,
                        help='Extract details for specific post ID')
    parser.add_argument('--limit', type=int,
                        help='Limit number of posts to process')
    parser.add_argument('--summary', action='store_true',
                        help='Show Firebase tracking summary')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                        help='Run browser with visible window')

    args = parser.parse_args()

    # Initialize Firebase tracker
    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    # If only summary requested
    if args.summary:
        tracker.print_summary()
        return

    # Load config
    config = load_config()

    # Authenticate
    auth = authenticate(config, headless=args.headless)

    if not auth:
        logger.error("❌ Authentication failed. Exiting.")
        return

    scraper = PatreonScraperV2(auth)

    try:
        if args.all:
            extract_all_pending(scraper, tracker, limit=args.limit)

        elif args.creator:
            extract_all_pending(scraper, tracker, creator_id=args.creator, limit=args.limit)

        elif args.post:
            extract_single_post(scraper, tracker, args.post)

        else:
            logger.error("❌ No action specified. Use --all, --creator, --post, or --summary")
            logger.info("Run with --help for usage information")

        # Show final summary
        logger.info("\n")
        tracker.print_summary()

    finally:
        logger.info("\n🎉 Phase 2 complete! Press ENTER to close browser...")
        input()
        auth.close()


if __name__ == "__main__":
    main()
