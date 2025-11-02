#!/usr/bin/env python3
"""
Orchestrator Script
Runs both phases automatically: URL collection + Detail extraction
"""

import json
import argparse
import logging
from pathlib import Path
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from firebase_tracker import FirebaseTracker, load_firebase_config
from phase1_url_collector import collect_urls_for_creator
from phase2_detail_extractor import extract_post_details

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from credentials.json"""
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        return json.load(f)


def authenticate(config, headless=True):
    """Authenticate with Patreon"""
    email = config['patreon']['email']
    password = config['patreon']['password']

    auth = PatreonAuthSelenium(email, password, headless=headless)

    if auth.load_cookies():
        logger.info("📂 Loaded existing cookies")
        if auth.is_authenticated():
            logger.info("✅ Already authenticated!")
            return auth
        else:
            logger.warning("⚠️  Cookies expired, need to login again")

    logger.info("🔐 Logging in to Patreon...")
    if not auth.login(manual_mode=False):
        logger.error("❌ Login failed!")
        return None

    auth.save_cookies()
    logger.info("✅ Authentication successful!")
    return auth


def run_full_workflow(
    config,
    auth,
    tracker: FirebaseTracker,
    limit_urls: int = None,
    limit_details: int = None,
    creator_filter: str = None
):
    """
    Run complete two-phase workflow

    Args:
        config: Configuration dictionary
        auth: Authenticated PatreonAuthSelenium instance
        tracker: FirebaseTracker instance
        limit_urls: Limit URLs to collect per creator
        limit_details: Limit posts to extract details
        creator_filter: Optional creator filter
    """
    scraper = PatreonScraperV2(auth)
    creators = config['patreon']['creators']

    # Filter creators if specified
    if creator_filter:
        creators = [c for c in creators if c['creator_id'] == creator_filter or c['name'].lower() == creator_filter.lower()]
        if not creators:
            logger.error(f"❌ Creator '{creator_filter}' not found")
            return

    logger.info("\n" + "="*70)
    logger.info("🚀 STARTING FULL TWO-PHASE WORKFLOW")
    logger.info("="*70)
    logger.info(f"Creators to process: {len(creators)}")
    logger.info(f"URL limit per creator: {limit_urls or 'None (all)'}")
    logger.info(f"Detail extraction limit: {limit_details or 'None (all pending)'}")
    logger.info("="*70 + "\n")

    total_stats = {
        "new_urls": 0,
        "details_extracted": 0,
        "details_failed": 0
    }

    for i, creator in enumerate(creators, 1):
        creator_id = creator['creator_id']
        creator_name = creator['name']

        logger.info(f"\n{'#'*70}")
        logger.info(f"# [{i}/{len(creators)}] PROCESSING CREATOR: {creator_name}")
        logger.info(f"{'#'*70}\n")

        try:
            # ========== PHASE 1: COLLECT URLs ==========
            logger.info(f"\n{'='*60}")
            logger.info(f"📥 PHASE 1: Collecting URLs from {creator_name}")
            logger.info(f"{'='*60}\n")

            new_urls = collect_urls_for_creator(
                scraper=scraper,
                tracker=tracker,
                creator=creator,
                limit=limit_urls
            )

            total_stats["new_urls"] += new_urls
            logger.info(f"\n✅ Phase 1 complete: {new_urls} new URLs collected")

            # ========== PHASE 2: EXTRACT DETAILS ==========
            logger.info(f"\n{'='*60}")
            logger.info(f"📄 PHASE 2: Extracting details for {creator_name}")
            logger.info(f"{'='*60}\n")

            # Get posts needing details for this creator
            posts_needing_details = tracker.get_posts_needing_details(creator_id)

            if not posts_needing_details:
                logger.info("✅ No posts need detail extraction for this creator")
                continue

            # Apply limit if specified
            if limit_details:
                posts_needing_details = posts_needing_details[:limit_details]

            logger.info(f"Found {len(posts_needing_details)} posts needing details")

            # Extract details for each post
            for j, post in enumerate(posts_needing_details, 1):
                logger.info(f"\n--- [{j}/{len(posts_needing_details)}] Extracting post {post['post_id']} ---")

                success = extract_post_details(scraper, tracker, post)

                if success:
                    total_stats["details_extracted"] += 1
                else:
                    total_stats["details_failed"] += 1

            # Update creator stats
            tracker.update_creator_stats(creator_id)

            logger.info(f"\n✅ Phase 2 complete for {creator_name}")

        except Exception as e:
            logger.error(f"❌ Error processing {creator_name}: {e}")
            continue

    # ========== FINAL SUMMARY ==========
    logger.info("\n" + "="*70)
    logger.info("🎉 TWO-PHASE WORKFLOW COMPLETE")
    logger.info("="*70)
    logger.info(f"New URLs collected:     {total_stats['new_urls']}")
    logger.info(f"Details extracted:      {total_stats['details_extracted']}")
    logger.info(f"Details failed:         {total_stats['details_failed']}")
    logger.info("="*70 + "\n")

    # Show Firebase summary
    tracker.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description='Orchestrator: Run complete two-phase workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete workflow for all creators
  python orchestrator.py --all

  # Run workflow with limits (5 URLs per creator, extract 10 details)
  python orchestrator.py --all --limit-urls 5 --limit-details 10

  # Run workflow for single creator
  python orchestrator.py --creator headonhistory

  # Show Firebase summary only
  python orchestrator.py --summary
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='Run workflow for all creators')
    parser.add_argument('--creator', type=str,
                        help='Run workflow for single creator')
    parser.add_argument('--limit-urls', type=int,
                        help='Limit URLs to collect per creator')
    parser.add_argument('--limit-details', type=int,
                        help='Limit posts to extract details')
    parser.add_argument('--summary', action='store_true',
                        help='Show Firebase tracking summary')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                        help='Run browser with visible window')

    args = parser.parse_args()

    # Initialize Firebase
    database_url, database_secret = load_firebase_config()
    tracker = FirebaseTracker(database_url, database_secret)

    # Show summary if requested
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
            run_full_workflow(
                config, auth, tracker,
                limit_urls=args.limit_urls,
                limit_details=args.limit_details
            )

        elif args.creator:
            run_full_workflow(
                config, auth, tracker,
                limit_urls=args.limit_urls,
                limit_details=args.limit_details,
                creator_filter=args.creator
            )

        else:
            logger.error("❌ No action specified. Use --all, --creator, or --summary")
            logger.info("Run with --help for usage information")

    finally:
        logger.info("\n🎉 Workflow complete! Press ENTER to close browser...")
        input()
        auth.close()


if __name__ == "__main__":
    main()
