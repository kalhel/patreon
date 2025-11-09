#!/usr/bin/env python3
"""
Test script to download a single post without Firebase
Useful for testing YouTube subtitle download and cleaning
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from patreon_auth_selenium import PatreonAuthSelenium
from patreon_scraper_v2 import PatreonScraperV2
from media_downloader import MediaDownloader
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent / "config" / "credentials.json"
    with open(config_path) as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_single_post.py <POST_URL>")
        print("\nExample:")
        print("  python test_single_post.py https://www.patreon.com/posts/123456789")
        sys.exit(1)

    post_url = sys.argv[1]

    # Extract creator and post ID from URL
    # URL format: https://www.patreon.com/posts/title-123456789
    parts = post_url.rstrip('/').split('/')
    post_id = parts[-1].split('-')[-1]  # Get the number at the end

    logger.info(f"📥 Testing single post download")
    logger.info(f"   URL: {post_url}")
    logger.info(f"   Post ID: {post_id}")

    # Load config
    config = load_config()
    email = config['patreon']['email']
    password = config['patreon']['password']

    # Authenticate
    logger.info("🔐 Authenticating...")
    auth = PatreonAuthSelenium(email, password, headless=False)

    if auth.load_cookies():
        logger.info("📂 Loaded existing cookies")
        if not auth.is_authenticated():
            logger.warning("⚠️  Cookies expired, logging in...")
            auth.login(manual_mode=False)
            auth.save_cookies()
    else:
        logger.info("🔐 Logging in...")
        auth.login(manual_mode=False)
        auth.save_cookies()

    # Create scraper
    scraper = PatreonScraperV2(auth)

    # Extract post details
    logger.info("📄 Extracting post details...")
    post_data = scraper.extract_post_details(post_url)

    if not post_data:
        logger.error("❌ Failed to extract post data")
        auth.close()
        return

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"POST DETAILS")
    logger.info(f"{'='*60}")
    logger.info(f"Title: {post_data.get('title', 'N/A')}")
    logger.info(f"Creator: {post_data.get('creator_name', 'N/A')}")
    logger.info(f"Published: {post_data.get('published_date', 'N/A')}")
    logger.info(f"Video URLs: {len(post_data.get('videos', []))}")
    logger.info(f"Video Downloads: {len(post_data.get('video_downloads', []))}")
    logger.info(f"YouTube embeds: {sum(1 for b in post_data.get('content_blocks', []) if b.get('type') == 'youtube_embed')}")
    logger.info(f"{'='*60}\n")

    # Download media
    creator_id = post_data.get('creator_id', 'unknown_creator')
    downloader = MediaDownloader()
    downloader.sync_cookies_from_driver(auth.driver)

    logger.info("📥 Downloading media...")
    result = downloader.download_all_from_post(post_data, creator_id)

    # Print results
    logger.info(f"\n{'='*60}")
    logger.info(f"DOWNLOAD RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"Videos: {len(result['videos'])}")
    logger.info(f"Subtitles: {len(result['video_subtitles'])}")
    logger.info(f"Images: {len(result['images'])}")
    logger.info(f"Audios: {len(result['audios'])}")
    logger.info(f"{'='*60}\n")

    if result['video_subtitles']:
        logger.info("✅ Subtitle files downloaded:")
        for sub in result['video_subtitles_relative']:
            logger.info(f"   • {sub}")

    # Save to JSON
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{creator_id}_{post_id}_test.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, indent=2, ensure_ascii=False)

    logger.info(f"\n💾 Saved to: {output_file}")

    logger.info("\n🎉 Test complete! Press ENTER to close browser...")
    input()
    auth.close()


if __name__ == "__main__":
    main()
