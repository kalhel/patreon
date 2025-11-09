#!/usr/bin/env python3
"""
Daily Incremental Scraper
Optimized for daily updates - only scrapes NEW content

Workflow:
1. Phase 1 Incremental: Collect only recent post URLs, stop at first known post
2. Phase 2: Extract details for pending posts only
3. Phase 3 Incremental: Check for new collections or posts in existing collections

Usage:
  python daily_incremental_scrape.py --all
  python daily_incremental_scrape.py --creator headonhistory
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from postgres_tracker import PostgresTracker
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from credentials.json and creators.json"""
    config_dir = Path(__file__).parent / "config"

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
    """Authenticate with Patreon"""
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


def incremental_collect_urls(scraper, tracker, creator, max_pages=3):
    """
    Collect URLs incrementally - stop when hitting known posts

    Args:
        scraper: PatreonScraperV2 instance
        tracker: PostgresTracker instance
        creator: Creator configuration
        max_pages: Maximum pages to check (default 3 = ~30-45 recent posts)

    Returns:
        Number of new URLs collected
    """
    creator_id = creator['creator_id']
    creator_url = creator['url']
    creator_name = creator['name']

    logger.info(f"\n{'='*60}")
    logger.info(f"📥 INCREMENTAL: Checking recent posts for {creator_name}")
    logger.info(f"   (Will stop at first known post)")
    logger.info(f"{'='*60}\n")

    # Get existing posts from database
    existing_posts = tracker.get_all_posts()
    existing_post_ids = set(existing_posts.keys())

    logger.info(f"📊 Existing posts in database: {len(existing_post_ids)}")

    # Scrape with early stop
    new_posts = []
    total_checked = 0
    consecutive_known = 0
    max_consecutive = 3  # Stop after 3 consecutive known posts

    try:
        # Scrape posts page by page
        for page_num in range(1, max_pages + 1):
            logger.info(f"\n📄 Checking page {page_num}...")

            # Get posts from this page
            page_posts = scraper.scrape_creator(
                creator_url=creator_url,
                creator_id=creator_id,
                skip_details=True,  # Only URLs, not full content
                max_posts=15 * page_num,  # Roughly 15 posts per page
                min_posts=15 * (page_num - 1)
            )

            if not page_posts:
                logger.info("   No more posts found, stopping")
                break

            # Process posts on this page
            page_new_count = 0
            for post in page_posts[15 * (page_num - 1):]:
                total_checked += 1
                post_id = post['post_id']

                # Check if already exists
                if post_id in existing_post_ids:
                    consecutive_known += 1
                    logger.info(f"   ⏭️  Post {post_id} already exists (skip {consecutive_known})")

                    # Stop if we've seen multiple known posts in a row
                    if consecutive_known >= max_consecutive:
                        logger.info(f"\n⏹️  Found {max_consecutive} consecutive known posts - stopping")
                        logger.info("   (All recent posts are already collected)")
                        break
                else:
                    # New post!
                    consecutive_known = 0
                    page_new_count += 1

                    logger.info(f"   ✨ NEW: {post_id} - {post.get('title', 'Untitled')[:50]}")

                    # Add to database
                    tracker.add_post(
                        post_id=post_id,
                        post_url=post['post_url'],
                        creator_id=creator_id,
                        title=post.get('title', ''),
                        published_date=post.get('published_date', ''),
                        metadata=post
                    )

                    new_posts.append(post)

            logger.info(f"   Page {page_num}: {page_new_count} new, {len(page_posts)} total")

            # Stop if we hit the consecutive limit
            if consecutive_known >= max_consecutive:
                break

    except Exception as e:
        logger.error(f"❌ Error during incremental scraping: {e}")

    # Update stats
    tracker.update_creator_stats(creator_id)

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 INCREMENTAL COLLECTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Posts checked:  {total_checked}")
    logger.info(f"New posts:      {len(new_posts)}")
    logger.info(f"Already known:  {total_checked - len(new_posts)}")
    logger.info(f"{'='*60}\n")

    return len(new_posts)


def incremental_scrape_single(config, auth, tracker, creator_name):
    """Run incremental scrape for single creator"""
    creators = config['patreon']['creators']

    # Find creator
    creator = None
    for c in creators:
        if c['creator_id'] == creator_name or c['name'].lower() == creator_name.lower():
            creator = c
            break

    if not creator:
        logger.error(f"❌ Creator '{creator_name}' not found")
        logger.info(f"Available: {', '.join([c['creator_id'] for c in creators])}")
        return

    scraper = PatreonScraperV2(auth)
    new_count = incremental_collect_urls(scraper, tracker, creator)

    logger.info(f"\n✅ Collected {new_count} new posts from {creator['name']}")


def incremental_scrape_all(config, auth, tracker):
    """Run incremental scrape for all creators"""
    scraper = PatreonScraperV2(auth)
    creators = config['patreon']['creators']

    total_new = 0

    for i, creator in enumerate(creators, 1):
        logger.info(f"\n🎯 [{i}/{len(creators)}] Processing {creator['name']}...")

        try:
            new_count = incremental_collect_urls(scraper, tracker, creator)
            total_new += new_count
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            continue

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 DAILY INCREMENTAL SCRAPE COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total new posts: {total_new}")
    logger.info(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Daily Incremental Scraper - Only collect NEW content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily update - check all creators for new posts
  python daily_incremental_scrape.py --all

  # Check single creator for new posts
  python daily_incremental_scrape.py --creator headonhistory

  # Check with visible browser (for debugging)
  python daily_incremental_scrape.py --all --no-headless

How it works:
  1. Scrapes only recent posts (first 3 pages ≈ 45 posts)
  2. Stops when it finds posts that already exist in database
  3. Much faster than full scrape (seconds vs minutes)
  4. Perfect for daily cron jobs

Perfect for:
  - Daily cron job to catch new posts
  - Quick updates without re-scraping everything
  - Efficient bandwidth usage
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Check all creators for new posts')
    parser.add_argument('--creator', type=str,
                        help='Check single creator (name or ID)')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                        help='Run browser with visible window')

    args = parser.parse_args()

    # Initialize PostgreSQL tracker
    tracker = PostgresTracker()

    # Load config
    config = load_config()

    # Authenticate
    auth = authenticate(config, headless=args.headless)
    if not auth:
        logger.error("❌ Authentication failed")
        return

    try:
        if args.all:
            incremental_scrape_all(config, auth, tracker)
        elif args.creator:
            incremental_scrape_single(config, auth, tracker, args.creator)
        else:
            logger.error("❌ Use --all or --creator")
            logger.info("Run with --help for usage")

        # Show summary
        logger.info("\n")
        tracker.print_summary()

    finally:
        logger.info("\n🎉 Incremental scrape complete! Press ENTER to close...")
        input()
        auth.close()


if __name__ == "__main__":
    main()
