#!/usr/bin/env python3
"""
Main script for Patreon to Notion project
Orchestrates scraping, processing, and uploading
"""

import json
import argparse
import logging
from pathlib import Path
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from credentials.json"""
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        return json.load(f)


def authenticate(config, headless=False):
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


def scrape_all_creators(config, auth, limit=None, full_details=False):
    """
    Scrape all creators from config

    Args:
        config: Configuration dictionary
        auth: Authenticated PatreonAuthSelenium instance
        limit: Max posts per creator (None = all)
        full_details: Whether to scrape full post details
    """
    scraper = PatreonScraperV2(auth)
    creators = config['patreon']['creators']

    for i, creator in enumerate(creators, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{i}/{len(creators)}] Scraping: {creator['name']}")
        logger.info(f"{'='*60}\n")

        try:
            # Scrape posts
            posts = scraper.scrape_creator(
                creator_url=creator['url'],
                creator_id=creator['creator_id'],
                limit=limit
            )

            # Save posts
            scraper.save_posts(posts, creator['creator_id'])

            # Optionally scrape full details
            if full_details and posts:
                logger.info(f"\n📄 Scraping full details for {len(posts)} posts...")

                for j, post in enumerate(posts, 1):
                    logger.info(f"  [{j}/{len(posts)}] {post['title'][:50]}...")

                    try:
                        post_detail = scraper.scrape_post_detail(post['post_url'])

                        # Merge detail into post
                        post.update(post_detail)

                    except Exception as e:
                        logger.error(f"    ❌ Error scraping detail: {e}")
                        continue

                # Save updated posts with full details
                scraper.save_posts(posts, creator['creator_id'])

            logger.info(f"✅ Completed {creator['name']}: {len(posts)} posts scraped\n")

        except Exception as e:
            logger.error(f"❌ Error scraping {creator['name']}: {e}\n")
            continue


def scrape_single_creator(config, auth, creator_name, limit=None, full_details=False):
    """
    Scrape a single creator

    Args:
        config: Configuration dictionary
        auth: Authenticated PatreonAuthSelenium instance
        creator_name: Name or ID of creator
        limit: Max posts to scrape (None = all)
        full_details: Whether to scrape full post details
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

    logger.info(f"🎯 Scraping: {creator['name']}")

    scraper = PatreonScraperV2(auth)

    # Scrape posts
    posts = scraper.scrape_creator(
        creator_url=creator['url'],
        creator_id=creator['creator_id'],
        limit=limit
    )

    # Save posts
    scraper.save_posts(posts, creator['creator_id'])

    # Optionally scrape full details
    if full_details and posts:
        logger.info(f"\n📄 Scraping full details for {len(posts)} posts...")

        for j, post in enumerate(posts, 1):
            logger.info(f"  [{j}/{len(posts)}] {post['title'][:50]}...")

            try:
                post_detail = scraper.scrape_post_detail(post['post_url'])
                post.update(post_detail)
            except Exception as e:
                logger.error(f"    ❌ Error: {e}")
                continue

        # Save updated posts
        scraper.save_posts(posts, creator['creator_id'])

    logger.info(f"✅ Completed: {len(posts)} posts scraped")


def main():
    parser = argparse.ArgumentParser(
        description='Patreon to Notion - Content Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all creators (preview only, limit 5 posts each)
  python main.py --scrape-all --limit 5

  # Scrape all posts from all creators with full details
  python main.py --scrape-all --full-details

  # Scrape single creator
  python main.py --creator headonhistory --limit 10

  # Scrape single creator with full details (images, videos, etc.)
  python main.py --creator astrobymax --full-details

  # Just authenticate and save cookies
  python main.py --auth-only
        """
    )

    parser.add_argument('--scrape-all', action='store_true',
                        help='Scrape all creators from config')
    parser.add_argument('--creator', type=str,
                        help='Scrape single creator (name or ID)')
    parser.add_argument('--limit', type=int,
                        help='Limit number of posts per creator')
    parser.add_argument('--full-details', action='store_true',
                        help='Scrape full post details (slower)')
    parser.add_argument('--auth-only', action='store_true',
                        help='Only authenticate and save cookies')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode')

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Authenticate
    auth = authenticate(config, headless=args.headless)

    if not auth:
        logger.error("❌ Authentication failed. Exiting.")
        return

    if args.auth_only:
        logger.info("✅ Authentication complete. Cookies saved.")
        auth.close()
        return

    try:
        if args.scrape_all:
            scrape_all_creators(config, auth, limit=args.limit, full_details=args.full_details)

        elif args.creator:
            scrape_single_creator(config, auth, args.creator, limit=args.limit, full_details=args.full_details)

        else:
            logger.error("❌ No action specified. Use --scrape-all or --creator")
            logger.info("Run with --help for usage information")

    finally:
        logger.info("\n🎉 Done! Press ENTER to close browser...")
        input()
        auth.close()


if __name__ == "__main__":
    main()
