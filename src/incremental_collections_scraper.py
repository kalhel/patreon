#!/usr/bin/env python3
"""
Incremental Collections Scraper
Only scrapes NEW or UPDATED collections (much faster for daily updates)
"""

import json
import argparse
import logging
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Set
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
        logging.FileHandler('logs/incremental_collections_scraper.log'),
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


def load_existing_collections(creator_id: str) -> Optional[Dict]:
    """
    Load existing collections data for a creator

    Args:
        creator_id: Creator identifier

    Returns:
        Existing collections data or None if file doesn't exist
    """
    collections_file = Path("data/processed") / f"{creator_id}_collections.json"

    if not collections_file.exists():
        logger.info(f"  ℹ️  No existing collections file for {creator_id}")
        return None

    try:
        with open(collections_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"  📂 Loaded {len(data.get('collections', []))} existing collections")
        return data
    except Exception as e:
        logger.error(f"  ❌ Error loading existing collections: {e}")
        return None


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


def download_collection_image(image_url: str, creator_id: str, collection_id: str) -> Optional[str]:
    """
    Download collection image and save locally

    Args:
        image_url: URL of the collection image
        creator_id: Creator identifier
        collection_id: Collection identifier

    Returns:
        Relative path to saved image or None if failed
    """
    if not image_url:
        logger.warning(f"    ⚠️  No image URL provided for collection {collection_id}")
        return None

    logger.info(f"    📥 Downloading collection image...")

    try:
        # Create directory structure
        images_dir = Path("data/media/collections") / creator_id
        images_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension from URL
        ext = ".jpg"  # Default
        if ".png" in image_url.lower():
            ext = ".png"
        elif ".jpeg" in image_url.lower() or ".jpg" in image_url.lower():
            ext = ".jpg"
        elif ".webp" in image_url.lower():
            ext = ".webp"

        # Save as collection_{id}{ext}
        filename = f"collection_{collection_id}{ext}"
        output_path = images_dir / filename

        # Download image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        # Save to file
        output_path.write_bytes(response.content)

        # Return relative path for JSON storage
        relative_path = f"collections/{creator_id}/{filename}"
        logger.info(f"    ✅ Image saved: {relative_path}")

        return relative_path

    except Exception as e:
        logger.error(f"    ❌ Failed to download collection image: {e}")
        return None


def extract_collection_metadata(driver, collection_element) -> Optional[Dict]:
    """
    Extract basic collection metadata from card (without navigating to collection)

    Args:
        driver: Selenium WebDriver instance
        collection_element: Selenium element representing a collection card

    Returns:
        Dictionary with basic collection data or None if extraction failed
    """
    try:
        # Find collection link
        try:
            link = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title-href"]')
            collection_url = link.get_attribute('href')
            collection_id = collection_url.split('/collection/')[-1].split('?')[0]
        except NoSuchElementException:
            logger.warning("  ⚠️  Could not find collection link")
            return None

        # Find collection name
        try:
            name_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title"]')
            collection_name = name_element.text.strip()
        except NoSuchElementException:
            collection_name = "Unnamed Collection"

        # Find collection image
        collection_image = None
        try:
            img_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-thumbnail"]')
            collection_image = img_element.get_attribute('imgurl')
        except NoSuchElementException:
            pass

        # Find post count
        post_count = 0
        try:
            count_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-num-post"]')
            post_count = int(count_element.text.strip())
        except (NoSuchElementException, ValueError):
            pass

        # Find description
        description = None
        try:
            desc_element = collection_element.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-description"]')
            description = desc_element.text.strip()
        except NoSuchElementException:
            pass

        return {
            "collection_id": collection_id,
            "collection_name": collection_name,
            "collection_url": collection_url,
            "collection_image": collection_image,
            "description": description,
            "post_count": post_count,
        }

    except Exception as e:
        logger.error(f"  ❌ Error extracting collection metadata: {e}")
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
    logger.info(f"    📂 Extracting posts from collection...")

    try:
        # Navigate to collection with condensed view
        if '?' in collection_url:
            collection_url = collection_url.split('?')[0]
        collection_url_condensed = f"{collection_url}?view=condensed"

        driver.get(collection_url_condensed)
        time.sleep(4)  # Wait for page load

        post_ids = []

        # Find all links to posts
        post_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/posts/"]')

        for link in post_links:
            href = link.get_attribute('href')
            if href and '/posts/' in href:
                try:
                    # Remove query parameters
                    url_without_params = href.split('?')[0]

                    # Get the part after /posts/
                    after_posts = url_without_params.split('/posts/')[-1]

                    # Try to extract post ID
                    if after_posts.isdigit():
                        post_id = after_posts
                    else:
                        # If it has dashes (title-name-123456), get the last part
                        parts = after_posts.split('-')
                        for part in reversed(parts):
                            if part.isdigit():
                                post_id = part
                                break
                        else:
                            continue

                    if post_id and post_id not in post_ids:
                        post_ids.append(post_id)

                except Exception as e:
                    logger.debug(f"    Could not extract post ID from {href}: {e}")
                    continue

        logger.info(f"    ✅ Found {len(post_ids)} posts")
        return post_ids

    except Exception as e:
        logger.error(f"    ❌ Error extracting post IDs: {e}")
        return []


def needs_update(existing_collection: Dict, new_metadata: Dict) -> bool:
    """
    Determine if a collection needs to be updated

    Args:
        existing_collection: Existing collection data
        new_metadata: New metadata from scraping

    Returns:
        True if collection needs update
    """
    # Check if post count changed
    existing_count = existing_collection.get('post_count', 0)
    new_count = new_metadata.get('post_count', 0)

    if existing_count != new_count:
        logger.info(f"    📊 Post count changed: {existing_count} → {new_count}")
        return True

    # Check if description changed
    if existing_collection.get('description') != new_metadata.get('description'):
        logger.info(f"    📝 Description changed")
        return True

    return False


def incremental_scrape_collections(
    auth: PatreonAuthSelenium,
    creator: Dict,
    existing_data: Optional[Dict]
) -> Optional[Dict]:
    """
    Incrementally scrape collections - only new/updated ones

    Args:
        auth: PatreonAuthSelenium instance
        creator: Creator configuration
        existing_data: Existing collections data

    Returns:
        Updated collections data
    """
    creator_id = creator['creator_id']
    creator_name = creator['name']

    logger.info(f"\n{'='*60}")
    logger.info(f"🔄 Incremental collections scrape: {creator_name}")
    logger.info(f"{'='*60}\n")

    # Build map of existing collections
    existing_collections_map = {}
    if existing_data:
        for coll in existing_data.get('collections', []):
            existing_collections_map[coll['collection_id']] = coll
        logger.info(f"  📂 Found {len(existing_collections_map)} existing collections")

    # Try both URL formats for collections page
    collections_urls = [
        f"https://www.patreon.com/cw/{creator_id}/collections",
        f"https://www.patreon.com/c/{creator_id}/collections"
    ]

    driver = auth.driver
    all_metadata = []

    # STEP 1: Get metadata for ALL collections from the collections page
    for collections_url in collections_urls:
        try:
            logger.info(f"🔍 Loading collections page: {collections_url}")
            driver.get(collections_url)
            time.sleep(5)

            # Find collection cards
            try:
                collection_links = driver.find_elements(By.CSS_SELECTOR, '[data-tag="box-collection-title-href"]')
                logger.info(f"  ✓ Found {len(collection_links)} collections on page")

                if not collection_links:
                    continue

                # Get parent containers
                collection_elements = []
                for link in collection_links:
                    parent = link
                    for level in range(10):
                        parent = parent.find_element(By.XPATH, '..')
                        try:
                            parent.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title"]')
                            parent.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-thumbnail"]')
                            collection_elements.append(parent)
                            break
                        except NoSuchElementException:
                            continue

                # Extract metadata from all collections
                for element in collection_elements:
                    metadata = extract_collection_metadata(driver, element)
                    if metadata:
                        all_metadata.append(metadata)

                if all_metadata:
                    break

            except NoSuchElementException:
                logger.warning(f"  ⚠️  No collection elements found")
                continue

        except Exception as e:
            logger.error(f"❌ Error loading collections page: {e}")
            continue

    if not all_metadata:
        logger.warning(f"⚠️  No collections found for {creator_name}")
        return existing_data if existing_data else None

    logger.info(f"\n  📊 Found {len(all_metadata)} collections on page")

    # STEP 2: Determine which collections need processing
    collections_to_process = []
    collections_to_skip = []

    for metadata in all_metadata:
        collection_id = metadata['collection_id']
        collection_name = metadata['collection_name']

        if collection_id not in existing_collections_map:
            # NEW collection
            logger.info(f"  🆕 NEW: {collection_name} (ID: {collection_id})")
            collections_to_process.append(metadata)
        else:
            existing = existing_collections_map[collection_id]
            if needs_update(existing, metadata):
                # UPDATED collection
                logger.info(f"  🔄 UPDATED: {collection_name} (ID: {collection_id})")
                collections_to_process.append(metadata)
            else:
                # UNCHANGED collection
                logger.info(f"  ✓ UNCHANGED: {collection_name} (ID: {collection_id}) - skipping")
                collections_to_skip.append(existing)

    logger.info(f"\n  📋 Processing {len(collections_to_process)} new/updated collections")
    logger.info(f"  ⏭️  Skipping {len(collections_to_skip)} unchanged collections")

    # STEP 3: Process only new/updated collections
    processed_collections = []

    for i, metadata in enumerate(collections_to_process, 1):
        logger.info(f"\n  [{i}/{len(collections_to_process)}] Processing: {metadata['collection_name']}")

        # Extract post IDs by visiting the collection
        post_ids = extract_post_ids_from_collection(driver, metadata['collection_url'])

        # Download collection image
        collection_image_local = None
        if metadata.get('collection_image'):
            logger.info(f"    📸 Downloading image...")
            collection_image_local = download_collection_image(
                metadata['collection_image'],
                creator_id,
                metadata['collection_id']
            )

        # Build complete collection data
        collection_data = {
            "collection_id": metadata['collection_id'],
            "collection_name": metadata['collection_name'],
            "collection_url": metadata['collection_url'],
            "collection_image": metadata['collection_image'],
            "collection_image_local": collection_image_local,
            "description": metadata.get('description'),
            "post_count": len(post_ids),
            "post_ids": post_ids,
            "scraped_at": datetime.now().isoformat()
        }

        processed_collections.append(collection_data)
        logger.info(f"    ✅ Processed: {len(post_ids)} posts")

    # STEP 4: Merge with existing unchanged collections
    all_collections = processed_collections + collections_to_skip

    # Sort by collection name for consistency
    all_collections.sort(key=lambda x: x.get('collection_name', ''))

    result = {
        "creator_id": creator_id,
        "creator_name": creator_name,
        "scraped_at": datetime.now().isoformat(),
        "collections": all_collections
    }

    logger.info(f"\n✅ Incremental scrape complete for {creator_name}")
    logger.info(f"  📊 Total collections: {len(all_collections)}")
    logger.info(f"  🆕 New/Updated: {len(processed_collections)}")
    logger.info(f"  ⏭️  Unchanged: {len(collections_to_skip)}")

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
                "collection_name": collection['collection_name'],
                "collection_image_local": collection.get('collection_image_local')
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
        description="Incremental Collections Scraper - Only scrapes new/updated collections"
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
        default=True,
        help='Update existing posts with collection information (default: True)'
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

    # Process each creator
    summary = {
        'total_creators': len(creators),
        'total_new_collections': 0,
        'total_updated_collections': 0,
        'total_unchanged_collections': 0,
        'details': []
    }

    for creator in creators:
        try:
            # Load existing collections data
            existing_data = load_existing_collections(creator['creator_id'])

            # Incremental scrape
            collections_data = incremental_scrape_collections(auth, creator, existing_data)

            if collections_data:
                save_collections_data(creator['creator_id'], collections_data)

                # Calculate stats
                existing_ids = set()
                if existing_data:
                    existing_ids = {c['collection_id'] for c in existing_data.get('collections', [])}

                new_ids = {c['collection_id'] for c in collections_data['collections']}
                num_new = len(new_ids - existing_ids)
                num_total = len(collections_data['collections'])
                num_unchanged = num_total - num_new if existing_data else 0

                summary['total_new_collections'] += num_new
                summary['total_unchanged_collections'] += num_unchanged

                summary['details'].append({
                    'creator_id': creator['creator_id'],
                    'creator_name': creator['name'],
                    'total_collections': num_total,
                    'new_collections': num_new,
                    'unchanged_collections': num_unchanged
                })

                # Update posts
                if args.update_posts:
                    update_posts_with_collections(creator['creator_id'])

        except Exception as e:
            logger.error(f"❌ Error processing {creator['name']}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    # Cleanup
    auth.close()

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("✅ Incremental Collections Scrape Complete!")
    logger.info("="*60)
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"  Creators processed: {summary['total_creators']}")
    logger.info(f"  🆕 New collections: {summary['total_new_collections']}")
    logger.info(f"  ⏭️  Unchanged collections: {summary['total_unchanged_collections']}")

    if summary['details']:
        logger.info(f"\n📋 DETAILS:")
        for detail in summary['details']:
            logger.info(f"\n  🎨 {detail['creator_name']} ({detail['creator_id']})")
            logger.info(f"     Total collections: {detail['total_collections']}")
            logger.info(f"     🆕 New: {detail['new_collections']}")
            logger.info(f"     ⏭️  Unchanged: {detail['unchanged_collections']}")

    logger.info("\n" + "="*60 + "\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
