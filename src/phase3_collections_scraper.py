#!/usr/bin/env python3
"""
Phase 3: Collections Scraper
Scrapes collection metadata and updates posts with collection membership
"""

import json
import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from patreon_auth_selenium import PatreonAuthSelenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase3_collections_scraper.log'),
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


def extract_collection_data(driver, collection_element) -> Optional[Dict]:
    """
    Extract collection metadata from a collection card element

    Args:
        driver: Selenium WebDriver instance
        collection_element: Selenium element representing a collection card

    Returns:
        Dictionary with collection data or None if extraction failed
    """
    try:
        # Try to find collection link
        try:
            link = collection_element.find_element(By.CSS_SELECTOR, 'a[href*="/collection/"]')
            collection_url = link.get_attribute('href')

            # Extract collection ID from URL
            # Format: https://www.patreon.com/collection/12345?filters...
            collection_id = collection_url.split('/collection/')[-1].split('?')[0]
        except NoSuchElementException:
            logger.warning("  ⚠️  Could not find collection link")
            return None

        # Try to find collection name
        try:
            # Common selectors for collection title
            name_element = collection_element.find_element(By.CSS_SELECTOR, 'h2, h3, [data-tag="collection-title"]')
            collection_name = name_element.text.strip()
        except NoSuchElementException:
            # Fallback to link text
            collection_name = link.text.strip() if link else "Unnamed Collection"

        # Try to find collection image
        collection_image = None
        try:
            img = collection_element.find_element(By.TAG_NAME, 'img')
            collection_image = img.get_attribute('src')
        except NoSuchElementException:
            logger.debug("  No image found for collection")

        # Try to find post count
        post_count = 0
        try:
            # Look for text like "15 posts" or similar
            text_content = collection_element.text
            if 'post' in text_content.lower():
                import re
                match = re.search(r'(\d+)\s*post', text_content.lower())
                if match:
                    post_count = int(match.group(1))
        except Exception:
            pass

        # Try to find description
        description = None
        try:
            desc_element = collection_element.find_element(By.CSS_SELECTOR, 'p, [data-tag="collection-description"]')
            description = desc_element.text.strip()
        except NoSuchElementException:
            pass

        collection_data = {
            "collection_id": collection_id,
            "collection_name": collection_name,
            "collection_url": collection_url,
            "collection_image": collection_image,
            "description": description,
            "post_count": post_count,
            "post_ids": [],  # Will be populated by clicking into the collection
            "scraped_at": datetime.now().isoformat()
        }

        logger.info(f"  ✓ Found collection: {collection_name} ({collection_id})")
        return collection_data

    except Exception as e:
        logger.error(f"  ❌ Error extracting collection data: {e}")
        return None


def extract_post_ids_from_collection(driver, collection_url: str) -> List[str]:
    """
    Navigate to a collection page and extract all post IDs

    Args:
        driver: Selenium WebDriver instance
        collection_url: URL of the collection

    Returns:
        List of post IDs in the collection
    """
    logger.info(f"  📂 Extracting posts from collection: {collection_url}")

    try:
        # Navigate to collection
        driver.get(collection_url)
        time.sleep(3)  # Wait for page load

        post_ids = []

        # Try multiple strategies to find post elements
        selectors = [
            'a[href*="/posts/"]',
            '[data-tag="post-card"] a',
            'article a[href*="/posts/"]'
        ]

        for selector in selectors:
            try:
                post_links = driver.find_elements(By.CSS_SELECTOR, selector)

                for link in post_links:
                    href = link.get_attribute('href')
                    if href and '/posts/' in href:
                        # Extract post ID from URL
                        # Format: https://www.patreon.com/posts/title-12345678
                        parts = href.rstrip('/').split('-')
                        if parts and parts[-1].isdigit():
                            post_id = parts[-1]
                            if post_id not in post_ids:
                                post_ids.append(post_id)

                if post_ids:
                    break  # Found posts with this selector
            except Exception:
                continue

        logger.info(f"  ✓ Found {len(post_ids)} posts in collection")
        return post_ids

    except Exception as e:
        logger.error(f"  ❌ Error extracting post IDs: {e}")
        return []


def scrape_collections_for_creator(
    auth: PatreonAuthSelenium,
    creator: Dict
) -> Optional[Dict]:
    """
    Scrape all collections for a single creator

    Args:
        auth: PatreonAuthSelenium instance
        creator: Creator configuration

    Returns:
        Dictionary with creator collections data
    """
    creator_id = creator['creator_id']
    creator_name = creator['name']

    logger.info(f"\n{'='*60}")
    logger.info(f"📚 Scraping collections for: {creator_name}")
    logger.info(f"{'='*60}\n")

    # Try both URL formats for collections page
    collections_urls = [
        f"https://www.patreon.com/cw/{creator_id}/collections",
        f"https://www.patreon.com/c/{creator_id}/collections"
    ]

    driver = auth.driver
    collections_data = []

    for collections_url in collections_urls:
        try:
            logger.info(f"🔍 Trying collections URL: {collections_url}")
            driver.get(collections_url)
            time.sleep(3)  # Wait for page load

            # Check if page loaded successfully (not 404)
            if "404" in driver.title or "not found" in driver.page_source.lower():
                logger.warning(f"  ⚠️  Collections page not found")
                continue

            # Try to find collection cards
            collection_selectors = [
                '[data-tag="collection-card"]',
                'a[href*="/collection/"]',
                'div[class*="collection"]'
            ]

            collection_elements = []
            for selector in collection_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        collection_elements = elements
                        logger.info(f"  ✓ Found {len(elements)} collection elements with selector: {selector}")
                        break
                except Exception:
                    continue

            if not collection_elements:
                logger.warning(f"  ⚠️  No collections found on page")
                continue

            # Extract data from each collection
            for element in collection_elements:
                collection_data = extract_collection_data(driver, element)
                if collection_data:
                    # Extract post IDs by visiting the collection
                    post_ids = extract_post_ids_from_collection(driver, collection_data['collection_url'])
                    collection_data['post_ids'] = post_ids
                    collection_data['post_count'] = len(post_ids)  # Update with actual count

                    collections_data.append(collection_data)

                    # Return to collections page
                    driver.get(collections_url)
                    time.sleep(2)

            # If we found collections, break (don't try other URL format)
            if collections_data:
                break

        except Exception as e:
            logger.error(f"❌ Error scraping collections from {collections_url}: {e}")
            continue

    if not collections_data:
        logger.warning(f"⚠️  No collections found for {creator_name}")
        return None

    result = {
        "creator_id": creator_id,
        "creator_name": creator_name,
        "scraped_at": datetime.now().isoformat(),
        "collections": collections_data
    }

    logger.info(f"\n✅ Found {len(collections_data)} collections for {creator_name}")
    for collection in collections_data:
        logger.info(f"  - {collection['collection_name']}: {collection['post_count']} posts")

    return result


def save_collections_data(creator_id: str, collections_data: Dict):
    """
    Save collections data to JSON file

    Args:
        creator_id: Creator identifier
        collections_data: Collections data dictionary
    """
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{creator_id}_collections.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(collections_data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Saved collections to: {output_file}")


def update_posts_with_collections(creator_id: str):
    """
    Update existing posts JSON with collection information

    Args:
        creator_id: Creator identifier
    """
    logger.info(f"\n🔄 Updating posts with collection data for {creator_id}...")

    data_dir = Path("data/processed")

    # Load collections data
    collections_file = data_dir / f"{creator_id}_collections.json"
    if not collections_file.exists():
        logger.error(f"❌ Collections file not found: {collections_file}")
        return

    with open(collections_file, 'r', encoding='utf-8') as f:
        collections_data = json.load(f)

    # Load posts data
    posts_file = data_dir / f"{creator_id}_posts_detailed.json"
    if not posts_file.exists():
        logger.error(f"❌ Posts file not found: {posts_file}")
        return

    with open(posts_file, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    # Create mapping of post_id -> collections
    post_collections_map = {}
    for collection in collections_data.get('collections', []):
        for post_id in collection.get('post_ids', []):
            if post_id not in post_collections_map:
                post_collections_map[post_id] = []
            post_collections_map[post_id].append({
                "collection_id": collection['collection_id'],
                "collection_name": collection['collection_name']
            })

    # Update posts
    updated_count = 0
    for post in posts:
        post_id = post.get('post_id')
        if post_id in post_collections_map:
            post['collections'] = post_collections_map[post_id]
            updated_count += 1

    # Save updated posts
    with open(posts_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Updated {updated_count} posts with collection data")
    logger.info(f"💾 Saved to: {posts_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 3: Scrape Patreon Collections"
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Scrape collections for all creators'
    )
    parser.add_argument(
        '--creator',
        type=str,
        help='Scrape collections for specific creator (e.g., astrobymax)'
    )
    parser.add_argument(
        '--update-posts',
        action='store_true',
        help='Update existing posts with collection information'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.creator:
        parser.error("Must specify either --all or --creator")

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"❌ Failed to load config: {e}")
        return 1

    # Authenticate
    auth = authenticate(config, headless=args.headless)
    if not auth:
        logger.error("❌ Authentication failed!")
        return 1

    # Determine which creators to process
    creators = config['patreon']['creators']
    if args.creator:
        creators = [c for c in creators if c['creator_id'] == args.creator]
        if not creators:
            logger.error(f"❌ Creator '{args.creator}' not found in config")
            return 1

    # Scrape collections for each creator
    for creator in creators:
        try:
            collections_data = scrape_collections_for_creator(auth, creator)

            if collections_data:
                save_collections_data(creator['creator_id'], collections_data)

                # Update posts if requested
                if args.update_posts:
                    update_posts_with_collections(creator['creator_id'])
            else:
                logger.warning(f"No collections data to save for {creator['name']}")

        except Exception as e:
            logger.error(f"❌ Error processing {creator['name']}: {e}")
            continue

    # Cleanup
    auth.close()

    logger.info("\n" + "="*60)
    logger.info("✅ Phase 3 Collections Scraping Complete!")
    logger.info("="*60 + "\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
