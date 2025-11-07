#!/usr/bin/env python3
"""
Incremental Scraper for Patreon Posts
Only scrapes new posts that haven't been processed before
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
from datetime import datetime
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper import PatreonScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/incremental_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IncrementalScraper:
    """Manages incremental scraping of Patreon posts"""

    def __init__(self, auth: PatreonAuthSelenium):
        """
        Initialize incremental scraper

        Args:
            auth: Authenticated PatreonAuthSelenium instance
        """
        self.auth = auth
        self.scraper = PatreonScraper(auth)
        self.state_dir = Path("data/state")
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_file(self, creator_id: str) -> Path:
        """Get state file path for a creator"""
        return self.state_dir / f"{creator_id}_state.json"

    def _load_state(self, creator_id: str) -> Dict:
        """
        Load scraping state for a creator

        Args:
            creator_id: Creator identifier

        Returns:
            State dictionary
        """
        state_file = self._get_state_file(creator_id)

        if not state_file.exists():
            return {
                'creator_id': creator_id,
                'last_scrape': None,
                'processed_post_ids': [],
                'total_posts': 0,
                'last_post_date': None
            }

        with open(state_file, 'r') as f:
            return json.load(f)

    def _save_state(self, creator_id: str, state: Dict):
        """
        Save scraping state for a creator

        Args:
            creator_id: Creator identifier
            state: State dictionary
        """
        state_file = self._get_state_file(creator_id)
        state['last_scrape'] = datetime.now().isoformat()

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"💾 Saved state: {len(state['processed_post_ids'])} posts tracked")

    def _get_existing_post_ids(self, creator_id: str) -> Set[str]:
        """
        Get set of post IDs that have already been scraped

        Args:
            creator_id: Creator identifier

        Returns:
            Set of post IDs
        """
        state = self._load_state(creator_id)
        return set(state['processed_post_ids'])

    def _load_existing_posts(self, creator_id: str) -> List[Dict]:
        """
        Load existing posts from JSON files

        Args:
            creator_id: Creator identifier

        Returns:
            List of existing posts
        """
        # Check both raw and processed directories
        raw_file = Path("data/raw") / f"{creator_id}_posts.json"
        processed_file = Path("data/processed") / f"{creator_id}_posts.json"

        posts = []

        # Load from processed first (most complete)
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                posts = json.load(f)
            logger.info(f"📂 Loaded {len(posts)} posts from processed file")
        elif raw_file.exists():
            with open(raw_file, 'r') as f:
                posts = json.load(f)
            logger.info(f"📂 Loaded {len(posts)} posts from raw file")

        return posts

    def scrape_new_posts(self, creator_url: str, creator_id: str, full_details: bool = False) -> Dict:
        """
        Scrape only new posts for a creator

        Args:
            creator_url: URL to creator's posts page
            creator_id: Creator identifier
            full_details: Whether to scrape full post details

        Returns:
            Dictionary with scraping results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"INCREMENTAL SCRAPE: {creator_id}")
        logger.info(f"{'='*60}\n")

        # Load state
        state = self._load_state(creator_id)
        existing_post_ids = set(state['processed_post_ids'])

        logger.info(f"📊 Previously processed: {len(existing_post_ids)} posts")
        if state['last_scrape']:
            logger.info(f"🕐 Last scrape: {state['last_scrape']}")

        # Load existing posts
        existing_posts = self._load_existing_posts(creator_id)
        existing_posts_dict = {p['post_id']: p for p in existing_posts}

        # Scrape posts (will get all, but we'll filter)
        logger.info(f"\n🔍 Scanning for new posts...")
        all_posts = self.scraper.scrape_creator(
            creator_url=creator_url,
            creator_id=creator_id,
            limit=None  # Scan all to find new ones
        )

        # Filter to only new posts
        new_posts = []
        updated_posts = []

        for post in all_posts:
            post_id = post['post_id']

            if post_id not in existing_post_ids:
                # This is a new post
                new_posts.append(post)
                logger.info(f"  ✨ NEW: {post['title'][:50]}")
            else:
                # Post exists, but keep it for merging
                updated_posts.append(existing_posts_dict.get(post_id, post))

        logger.info(f"\n📈 Found {len(new_posts)} new posts")
        logger.info(f"📋 Kept {len(updated_posts)} existing posts")

        # Scrape full details for new posts only
        if full_details and new_posts:
            logger.info(f"\n📄 Scraping full details for {len(new_posts)} new posts...")

            for i, post in enumerate(new_posts, 1):
                logger.info(f"  [{i}/{len(new_posts)}] {post['title'][:50]}...")

                try:
                    post_detail = self.scraper.scrape_post_detail(post['post_url'])
                    post.update(post_detail)
                except Exception as e:
                    logger.error(f"    ❌ Error: {e}")
                    continue

        # Merge new and existing posts
        all_posts_merged = updated_posts + new_posts

        # Sort by post_id (descending - newest first)
        all_posts_merged.sort(key=lambda x: int(x.get('post_id', 0)), reverse=True)

        # Save merged posts
        self.scraper.save_posts(all_posts_merged, creator_id, output_dir="data/raw")

        # Update state
        state['processed_post_ids'] = [p['post_id'] for p in all_posts_merged]
        state['total_posts'] = len(all_posts_merged)

        # Get latest post date
        if all_posts_merged:
            latest_date = max(
                (p.get('published_at') for p in all_posts_merged if p.get('published_at')),
                default=None
            )
            state['last_post_date'] = latest_date

        self._save_state(creator_id, state)

        result = {
            'creator_id': creator_id,
            'new_posts': len(new_posts),
            'existing_posts': len(updated_posts),
            'total_posts': len(all_posts_merged),
            'new_post_ids': [p['post_id'] for p in new_posts]
        }

        logger.info(f"\n✅ Incremental scrape complete:")
        logger.info(f"   ✨ New posts: {result['new_posts']}")
        logger.info(f"   📋 Existing posts: {result['existing_posts']}")
        logger.info(f"   📊 Total posts: {result['total_posts']}")

        return result

    def scrape_all_creators_incremental(self, creators: List[Dict], full_details: bool = False) -> Dict:
        """
        Incrementally scrape all creators

        Args:
            creators: List of creator configurations
            full_details: Whether to scrape full details

        Returns:
            Summary of all scraping operations
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"INCREMENTAL SCRAPE - ALL CREATORS")
        logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}\n")

        summary = {
            'started_at': datetime.now().isoformat(),
            'creators_processed': 0,
            'total_new_posts': 0,
            'total_existing_posts': 0,
            'creators': []
        }

        for i, creator in enumerate(creators, 1):
            logger.info(f"\n{'─'*60}")
            logger.info(f"[{i}/{len(creators)}] {creator['name']}")
            logger.info(f"{'─'*60}")

            try:
                result = self.scrape_new_posts(
                    creator_url=creator['url'],
                    creator_id=creator['creator_id'],
                    full_details=full_details
                )

                summary['creators_processed'] += 1
                summary['total_new_posts'] += result['new_posts']
                summary['total_existing_posts'] += result['existing_posts']
                summary['creators'].append(result)

            except Exception as e:
                logger.error(f"❌ Error scraping {creator['name']}: {e}")
                summary['creators'].append({
                    'creator_id': creator['creator_id'],
                    'error': str(e)
                })
                continue

        summary['completed_at'] = datetime.now().isoformat()

        # Save summary
        summary_file = self.state_dir / f"scrape_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info("INCREMENTAL SCRAPE SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"✨ Total new posts: {summary['total_new_posts']}")
        logger.info(f"📋 Total existing posts: {summary['total_existing_posts']}")
        logger.info(f"👥 Creators processed: {summary['creators_processed']}/{len(creators)}")
        logger.info(f"💾 Summary saved: {summary_file}")
        logger.info(f"{'='*60}\n")

        return summary

    def get_stats(self, creator_id: Optional[str] = None) -> Dict:
        """
        Get scraping statistics

        Args:
            creator_id: Optional creator ID, if None returns all

        Returns:
            Statistics dictionary
        """
        if creator_id:
            state = self._load_state(creator_id)
            return {
                'creator_id': creator_id,
                'total_posts': state['total_posts'],
                'last_scrape': state['last_scrape'],
                'last_post_date': state['last_post_date']
            }

        # Get stats for all creators
        stats = []
        for state_file in self.state_dir.glob("*_state.json"):
            with open(state_file, 'r') as f:
                state = json.load(f)
                stats.append({
                    'creator_id': state['creator_id'],
                    'total_posts': state['total_posts'],
                    'last_scrape': state['last_scrape'],
                    'last_post_date': state['last_post_date']
                })

        return {'creators': stats}

    def reset_state(self, creator_id: str):
        """
        Reset state for a creator (forces full rescrape)

        Args:
            creator_id: Creator identifier
        """
        state_file = self._get_state_file(creator_id)
        if state_file.exists():
            state_file.unlink()
            logger.info(f"🔄 Reset state for {creator_id}")
        else:
            logger.info(f"⚠️  No state found for {creator_id}")


def main():
    """Test incremental scraper"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Incremental Patreon Scraper - Only scrape new posts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape new posts from all creators
  python incremental_scraper.py --scrape-all

  # Scrape new posts with full details
  python incremental_scraper.py --scrape-all --full-details

  # Scrape single creator
  python incremental_scraper.py --creator headonhistory

  # View statistics
  python incremental_scraper.py --stats

  # Reset state (force full rescrape)
  python incremental_scraper.py --reset headonhistory
        """
    )

    parser.add_argument('--scrape-all', action='store_true',
                        help='Incrementally scrape all creators')
    parser.add_argument('--creator', type=str,
                        help='Scrape single creator (name or ID)')
    parser.add_argument('--full-details', action='store_true',
                        help='Scrape full post details for new posts')
    parser.add_argument('--stats', action='store_true',
                        help='Show scraping statistics')
    parser.add_argument('--reset', type=str,
                        help='Reset state for a creator (forces full rescrape)')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode')

    args = parser.parse_args()

    # Load config
    config_path = Path(__file__).parent.parent / "config" / "credentials.json"
    with open(config_path) as f:
        config = json.load(f)

    # Initialize incremental scraper (needs auth)
    if not args.stats and not args.reset:
        email = config['patreon']['email']
        password = config['patreon']['password']
        auth = PatreonAuthSelenium(email, password, headless=args.headless)

        # Load cookies
        if auth.load_cookies():
            logger.info("📂 Loaded existing cookies")
            if not auth.is_authenticated():
                logger.warning("⚠️  Cookies expired, need to login")
                if not auth.login(manual_mode=True):
                    logger.error("❌ Login failed")
                    return
                auth.save_cookies()
        else:
            logger.info("🔐 Logging in...")
            if not auth.login(manual_mode=True):
                logger.error("❌ Login failed")
                return
            auth.save_cookies()

        scraper = IncrementalScraper(auth)
    else:
        scraper = IncrementalScraper(None)

    try:
        if args.stats:
            # Show statistics
            stats = scraper.get_stats()
            logger.info(f"\n{'='*60}")
            logger.info("SCRAPING STATISTICS")
            logger.info(f"{'='*60}\n")

            for creator_stats in stats['creators']:
                logger.info(f"📊 {creator_stats['creator_id']}")
                logger.info(f"   Total posts: {creator_stats['total_posts']}")
                logger.info(f"   Last scrape: {creator_stats['last_scrape']}")
                logger.info(f"   Last post: {creator_stats['last_post_date']}")
                logger.info("")

        elif args.reset:
            # Reset state
            scraper.reset_state(args.reset)

        elif args.scrape_all:
            # Scrape all creators incrementally
            creators = config['patreon']['creators']
            summary = scraper.scrape_all_creators_incremental(
                creators=creators,
                full_details=args.full_details
            )

            if summary['total_new_posts'] > 0:
                logger.info(f"\n✨ Found {summary['total_new_posts']} new posts!")
                logger.info(f"💡 Next steps:")
                logger.info(f"   1. Download media: python src/media_downloader.py --all")
                logger.info(f"   2. Generate tags: python src/tag_generator.py --all")
            else:
                logger.info(f"\n✅ No new posts found. Everything is up to date!")

        elif args.creator:
            # Scrape single creator
            creators = config['patreon']['creators']
            creator = None

            for c in creators:
                if c['creator_id'] == args.creator or c['name'].lower() == args.creator.lower():
                    creator = c
                    break

            if not creator:
                logger.error(f"❌ Creator '{args.creator}' not found")
                logger.info(f"Available: {', '.join([c['creator_id'] for c in creators])}")
                return

            result = scraper.scrape_new_posts(
                creator_url=creator['url'],
                creator_id=creator['creator_id'],
                full_details=args.full_details
            )

            if result['new_posts'] > 0:
                logger.info(f"\n✨ Found {result['new_posts']} new posts!")
            else:
                logger.info(f"\n✅ No new posts. Up to date!")

        else:
            logger.error("❌ No action specified. Use --scrape-all, --creator, --stats, or --reset")
            logger.info("Run with --help for usage information")

    finally:
        if not args.stats and not args.reset:
            logger.info("\n🎉 Done! Press ENTER to close browser...")
            input()
            auth.close()


if __name__ == "__main__":
    main()
