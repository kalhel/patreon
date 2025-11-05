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
        # Find collection link using data-tag
        try:
            link = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title-href"]')
            collection_url = link.get_attribute('href')

            # Extract collection ID from URL
            # Format: https://www.patreon.com/collection/12345
            collection_id = collection_url.split('/collection/')[-1].split('?')[0]
        except NoSuchElementException:
            logger.warning("  ⚠️  Could not find collection link")
            return None

        # Find collection name using data-tag
        try:
            name_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title"]')
            collection_name = name_element.text.strip()
        except NoSuchElementException:
            collection_name = "Unnamed Collection"
            logger.warning(f"  ⚠️  Could not find collection name for {collection_id}")

        # Find collection image from data-tag with imgurl attribute
        collection_image = None
        try:
            img_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-thumbnail"]')
            collection_image = img_element.get_attribute('imgurl')
        except NoSuchElementException:
            logger.debug("  No image found for collection")

        # Find post count using data-tag
        post_count = 0
        try:
            count_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-num-post"]')
            post_count = int(count_element.text.strip())
        except (NoSuchElementException, ValueError):
            logger.debug("  No post count found for collection")

        # Find description using data-tag (optional)
        description = None
        try:
            desc_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-description"]')
            description = desc_element.text.strip()
        except NoSuchElementException:
            pass  # Description is optional

        collection_data = {
            "collection_id": collection_id,
            "collection_name": collection_name,
            "collection_url": collection_url,
            "collection_image": collection_image,
            "description": description,
            "post_count": post_count,
            "post_ids": [],  # Will be populated by visiting the collection
            "scraped_at": datetime.now().isoformat()
        }

        logger.info(f"  ✓ Found collection: {collection_name} (ID: {collection_id}, Posts: {post_count})")
        return collection_data

    except Exception as e:
        logger.error(f"  ❌ Error extracting collection data: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
        # Navigate to collection with condensed view
        if '?' in collection_url:
            collection_url = collection_url.split('?')[0]
        collection_url_condensed = f"{collection_url}?view=condensed"

        driver.get(collection_url_condensed)
        time.sleep(4)  # Wait for page load

        post_ids = []

        # Find all links to posts
        # Format: https://www.patreon.com/posts/116593622?collection=1815761
        post_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/posts/"]')

        for link in post_links:
            href = link.get_attribute('href')
            if href and '/posts/' in href:
                try:
                    # Extract post ID from URL
                    # Format options:
                    # 1. https://www.patreon.com/posts/116593622?collection=...
                    # 2. https://www.patreon.com/posts/title-name-116593622

                    # Remove query parameters
                    url_without_params = href.split('?')[0]

                    # Get the part after /posts/
                    after_posts = url_without_params.split('/posts/')[-1]

                    # Try to extract post ID
                    # If it's just numbers, use it directly
                    if after_posts.isdigit():
                        post_id = after_posts
                    else:
                        # If it has dashes (title-name-123456), get the last part
                        parts = after_posts.split('-')
                        # Find the last numeric part
                        for part in reversed(parts):
                            if part.isdigit():
                                post_id = part
                                break
                        else:
                            continue  # Skip if no numeric ID found

                    if post_id and post_id not in post_ids:
                        post_ids.append(post_id)

                except Exception as e:
                    logger.debug(f"  Could not extract post ID from {href}: {e}")
                    continue

        logger.info(f"  ✓ Found {len(post_ids)} posts in collection")
        return post_ids

    except Exception as e:
        logger.error(f"  ❌ Error extracting post IDs: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
            time.sleep(5)  # Wait for page load and dynamic content

            # Look for the Collections heading to confirm we're on the right page
            try:
                heading = driver.find_element(By.XPATH, "//h1[contains(text(), 'Collections')]")
                logger.info(f"  ✓ Found Collections page")
            except NoSuchElementException:
                logger.warning(f"  ⚠️  Collections heading not found, may not be the right page")
                # Continue anyway, might still work

            # Find collection cards by looking for elements with collection title links
            # Each collection card contains a [data-tag="box-collection-title-href"] element
            try:
                collection_links = driver.find_elements(By.CSS_SELECTOR, '[data-tag="box-collection-title-href"]')
                logger.info(f"  ✓ Found {len(collection_links)} collections")

                if not collection_links:
                    logger.warning(f"  ⚠️  No collections found on page")
                    continue

                # For each collection link, find its parent container to extract all data
                collection_elements = []
                for link in collection_links:
                    # Navigate up to find the parent container with all collection data
                    # Usually 4-5 levels up
                    parent = link
                    for _ in range(6):
                        parent = parent.find_element(By.XPATH, '..')
                        # Check if this parent contains all the data-tags we need
                        try:
                            parent.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title"]')
                            collection_elements.append(parent)
                            break
                        except NoSuchElementException:
                            continue

                logger.info(f"  ✓ Found {len(collection_elements)} collection card elements")

            except NoSuchElementException:
                logger.warning(f"  ⚠️  No collection elements found")
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
