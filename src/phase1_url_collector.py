#!/usr/bin/env python3
"""
Phase 1: URL Collector
Collects all post URLs from Patreon creators and tracks them in Firebase
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from firebase_tracker import FirebaseTracker, load_firebase_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase1_url_collector.log'),
        logging.StreamHandler()
    ]
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
    with open(creators_path) as f:
        creators_data = json.load(f)
        config['patreon']['creators'] = creators_data.get('creators', [])

    return config


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


def collect_urls_for_creator(
    scraper: PatreonScraperV2,
    tracker: FirebaseTracker,
    creator: Dict,
    limit: int = None
) -> int:
    """
    Collect all post URLs for a single creator

    Args:
        scraper: PatreonScraperV2 instance
        tracker: FirebaseTracker instance
        creator: Creator configuration
        limit: Optional limit on posts to collect

    Returns:
        Number of new URLs collected
    """
    creator_id = creator['creator_id']
    creator_url = creator['url']
    creator_name = creator['name']

    logger.info(f"\n{'='*60}")
    logger.info(f"📥 Collecting URLs for: {creator_name}")
    logger.info(f"{'='*60}\n")

    # Scrape posts (URLs and basic info only)
    posts = scraper.scrape_creator(
        creator_url=creator_url,
        creator_id=creator_id,
        limit=limit
    )

    logger.info(f"\n📊 Found {len(posts)} posts from {creator_name}")

    # Track in Firebase
    new_posts = 0
    existing_posts = 0

    for post in posts:
        post_id = post['post_id']
        post_url = post['post_url']

        # Check if already in Firebase
        if tracker.post_exists(post_id):
            existing_posts += 1
            logger.info(f"  ⏭️  Post {post_id} already exists in Firebase")
            continue

        # Create new record in Firebase
        success = tracker.create_post_record(
            post_id=post_id,
            creator_id=creator_id,
            post_url=post_url
        )

        if success:
            new_posts += 1
            logger.info(f"  ✅ Tracked new post: {post_id}")
        else:
            logger.error(f"  ❌ Failed to track post: {post_id}")

    # Update creator stats
    tracker.update_creator_stats(creator_id)

    logger.info(f"\n📈 Summary for {creator_name}:")
    logger.info(f"  New posts:      {new_posts}")
    logger.info(f"  Existing posts: {existing_posts}")
    logger.info(f"  Total found:    {len(posts)}")

    return new_posts


def collect_all_urls(config, auth, tracker: FirebaseTracker, limit: int = None):
    """
    Collect URLs from all creators

    Args:
        config: Configuration dictionary
        auth: Authenticated PatreonAuthSelenium instance
        tracker: FirebaseTracker instance
        limit: Optional limit per creator
    """
    scraper = PatreonScraperV2(auth)
    creators = config['patreon']['creators']

    total_new = 0

    for i, creator in enumerate(creators, 1):
        logger.info(f"\n🎯 [{i}/{len(creators)}] Processing creator...")

        try:
            new_count = collect_urls_for_creator(
                scraper=scraper,
                tracker=tracker,
                creator=creator,
                limit=limit
            )
            total_new += new_count

        except Exception as e:
            logger.error(f"❌ Error collecting URLs for {creator['name']}: {e}")
            continue

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 PHASE 1 COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total new URLs collected: {total_new}")
    logger.info(f"{'='*60}\n")


def collect_single_creator(config, auth, tracker: FirebaseTracker, creator_name: str, limit: int = None):
    """
    Collect URLs from a single creator

    Args:
        config: Configuration dictionary
        auth: Authenticated PatreonAuthSelenium instance
        tracker: FirebaseTracker instance
        creator_name: Creator name or ID
        limit: Optional limit on posts
    """
    creators = config['patreon']['creators']

    # Find creator
    creator = None
    for c in creators:
        if c['creator_id'] == creator_name or c['name'].lower() == creator_name.lower():
            creator = c
            break

    if not creator:
        logger.error(f"❌ Creator '{creator_name}' not found in config")
        logger.info(f"Available creators: {', '.join([c['creator_id'] for c in creators])}")
        return

    scraper = PatreonScraperV2(auth)

    try:
        new_count = collect_urls_for_creator(
            scraper=scraper,
            tracker=tracker,
            creator=creator,
            limit=limit
        )

        logger.info(f"\n✅ Collected {new_count} new URLs from {creator['name']}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Phase 1: Collect Patreon Post URLs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect URLs from all creators
  python phase1_url_collector.py --all

  # Collect URLs from all creators (limit 10 per creator)
  python phase1_url_collector.py --all --limit 10

  # Collect URLs from single creator
  python phase1_url_collector.py --creator headonhistory

  # Show Firebase summary
  python phase1_url_collector.py --summary
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Collect URLs from all creators')
    parser.add_argument('--creator', type=str,
                        help='Collect URLs from single creator (name or ID)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of posts per creator')
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

    try:
        if args.all:
            collect_all_urls(config, auth, tracker, limit=args.limit)

        elif args.creator:
            collect_single_creator(config, auth, tracker, args.creator, limit=args.limit)

        else:
            logger.error("❌ No action specified. Use --all, --creator, or --summary")
            logger.info("Run with --help for usage information")

        # Show final summary
        logger.info("\n")
        tracker.print_summary()

    finally:
        logger.info("\n🎉 Phase 1 complete! Press ENTER to close browser...")
        input()
        auth.close()


if __name__ == "__main__":
    main()
