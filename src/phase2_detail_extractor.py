#!/usr/bin/env python3
"""
Phase 2: Post Detail Extractor
Extracts full details from posts tracked in PostgreSQL
"""

import json
import argparse
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from postgres_tracker import PostgresTracker
from media_downloader import MediaDownloader

# Load environment variables
load_dotenv()

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


# ============================================================================
# PostgreSQL Integration Functions
# ============================================================================

def use_postgresql() -> bool:
    """Check if PostgreSQL mode is enabled via flag file"""
    flag_path = Path("config/use_postgresql.flag")
    return flag_path.exists()


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables"""
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env file")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def update_post_details_in_postgres(post_data: Dict):
    """
    Update post in PostgreSQL with full extracted details

    Args:
        post_data: Full post data including extracted details
    """
    try:
        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Update post with full details
            update_sql = text("""
                UPDATE posts
                SET
                    title = :title,
                    content = :content,
                    content_blocks = CAST(:content_blocks AS jsonb),
                    published_at = :published_at,
                    edited_at = :edited_at,
                    video_streams = CAST(:video_streams AS jsonb),
                    video_subtitles = CAST(:video_subtitles AS jsonb),
                    video_local_paths = :video_local_paths,
                    video_subtitles_relative = :video_subtitles_relative,
                    audios = :audios,
                    audio_local_paths = :audio_local_paths,
                    images = :images,
                    image_local_paths = :image_local_paths,
                    patreon_tags = :patreon_tags,
                    updated_at = NOW()
                WHERE post_id = :post_id
            """)

            # Prepare data for update
            update_params = {
                'post_id': post_data.get('post_id'),
                'title': post_data.get('title'),
                'content': post_data.get('content'),
                'content_blocks': json.dumps(post_data.get('content_blocks', [])),
                'published_at': post_data.get('published_at'),
                'edited_at': post_data.get('edited_at'),
                'video_streams': json.dumps(post_data.get('video_streams', [])),
                'video_subtitles': json.dumps(post_data.get('video_subtitles', [])),
                'video_local_paths': post_data.get('video_local_paths'),
                'video_subtitles_relative': post_data.get('video_subtitles_relative'),
                'audios': post_data.get('audios'),
                'audio_local_paths': post_data.get('audio_local_paths'),
                'images': post_data.get('images'),
                'image_local_paths': post_data.get('image_local_paths'),
                'patreon_tags': post_data.get('patreon_tags')
            }

            conn.execute(update_sql, update_params)
            conn.commit()

            logger.info(f"   🐘 Updated post {post_data.get('post_id')} in PostgreSQL")

    except Exception as e:
        logger.error(f"   ❌ Error updating PostgreSQL: {e}")
        raise


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
    tracker: PostgresTracker,
    post: Dict,
    save_to_json: bool = True
) -> bool:
    """
    Extract full details for a single post

    Args:
        scraper: PatreonScraperV2 instance
        tracker: PostgresTracker instance
        post: Post record from database
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
            **post,  # Existing database data
            **post_detail  # New scraped details
        }

        # CRITICAL: Always preserve the creator_id from database
        # The scraper might extract incorrect creator info from page HTML
        full_post_data['creator_id'] = creator_id

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

            logger.info(f"   💾 Saved to JSON: {output_file}")

        # DUAL MODE: Also save to PostgreSQL if flag is enabled
        if use_postgresql():
            try:
                logger.info(f"   🐘 PostgreSQL mode enabled - updating database...")
                update_post_details_in_postgres(full_post_data)
            except Exception as e:
                logger.warning(f"   ⚠️  PostgreSQL update failed (continuing): {e}")

        # Mark as extracted in database
        tracker.mark_details_extracted(post_id, success=True)

        # Filter videos to only include actual video files (not images)
        video_extensions = ('.mp4', '.webm', '.ogg', '.mov', '.avi', '.m3u8', '.ts')
        actual_videos = [v for v in post_detail.get('videos', [])
                        if any(v.lower().split('?')[0].endswith(ext) for ext in video_extensions)]

        logger.info(f"   ✅ Successfully extracted details for post {post_id}")
        logger.info(f"      - Title: {post_detail.get('title', 'N/A')}")
        logger.info(f"      - Images: {len(post_detail.get('images', []))}")
        logger.info(f"      - Videos: {len(actual_videos)}")
        logger.info(f"      - Audios: {len(post_detail.get('audios', []))}")
        logger.info(f"      - Tags: {len(post_detail.get('patreon_tags', []))}")

        return True

    except Exception as e:
        logger.exception(f"   ❌ Error extracting post {post_id}")
        tracker.mark_details_extracted(post_id, success=False, error=str(e))
        return False


def extract_all_pending(
    scraper: PatreonScraperV2,
    tracker: PostgresTracker,
    creator_id: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, int]:
    """
    Extract details for all posts needing extraction

    Args:
        scraper: PatreonScraperV2 instance
        tracker: PostgresTracker instance
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
    tracker: PostgresTracker,
    post_id: str
) -> bool:
    """
    Extract details for a specific post

    Args:
        scraper: PatreonScraperV2 instance
        tracker: PostgresTracker instance
        post_id: Post ID to extract

    Returns:
        True if successful
    """
    # Get post from database
    post = tracker.get_post(post_id)

    if not post:
        logger.error(f"❌ Post {post_id} not found in database")
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

  # Show PostgreSQL summary
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
                        help='Show PostgreSQL tracking summary')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_false', dest='headless',
                        help='Run browser with visible window')

    args = parser.parse_args()

    # Initialize PostgreSQL tracker
    tracker = PostgresTracker()

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
