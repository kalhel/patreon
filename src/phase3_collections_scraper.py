#!/usr/bin/env python3
"""
Phase 3: Collections Scraper
Scrapes collection metadata and updates posts with collection membership

DUAL MODE: Saves to both JSON (always) and PostgreSQL (if flag enabled)
"""

import json
import argparse
import logging
import time
import requests
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus
from patreon_auth_selenium import PatreonAuthSelenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

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


# ============================================================================
# PostgreSQL Integration (Dual Mode)
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


def save_collections_to_postgres(creator_id: str, collections_data: Dict):
    """
    Save collections data to PostgreSQL database

    Args:
        creator_id: Creator identifier
        collections_data: Collections data dictionary from scraping
    """
    try:
        logger.info("  🐘 Saving to PostgreSQL...")

        # Create database engine and session
        engine = create_engine(get_database_url())
        Session = sessionmaker(bind=engine)
        session = Session()

        stats = {
            'collections_inserted': 0,
            'collections_skipped': 0,
            'relationships_inserted': 0,
            'relationships_skipped': 0
        }

        for collection in collections_data.get('collections', []):
            collection_id = collection['collection_id']

            try:
                # Insert or update collection
                insert_sql = text("""
                    INSERT INTO collections (
                        collection_id,
                        creator_id,
                        title,
                        description,
                        collection_url,
                        post_count,
                        collection_image,
                        collection_image_local,
                        scraped_at,
                        created_at
                    ) VALUES (
                        :collection_id,
                        :creator_id,
                        :title,
                        :description,
                        :collection_url,
                        :post_count,
                        :collection_image,
                        :collection_image_local,
                        :scraped_at,
                        NOW()
                    )
                    ON CONFLICT (collection_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        collection_url = EXCLUDED.collection_url,
                        post_count = EXCLUDED.post_count,
                        collection_image = EXCLUDED.collection_image,
                        collection_image_local = EXCLUDED.collection_image_local,
                        scraped_at = EXCLUDED.scraped_at,
                        updated_at = NOW()
                    RETURNING id
                """)

                result = session.execute(insert_sql, {
                    'collection_id': collection_id,
                    'creator_id': creator_id,
                    'title': collection['collection_name'],
                    'description': collection.get('description'),
                    'collection_url': collection.get('collection_url'),
                    'post_count': collection.get('post_count', 0),
                    'collection_image': collection.get('collection_image'),
                    'collection_image_local': collection.get('collection_image_local'),
                    'scraped_at': collection.get('scraped_at')
                })
                session.commit()

                if result.rowcount > 0:
                    stats['collections_inserted'] += 1
                    logger.info(f"    ✓ Collection saved: {collection['collection_name']}")
                else:
                    stats['collections_skipped'] += 1

                # Insert post-collection relationships
                for order, post_id in enumerate(collection.get('post_ids', []), start=1):
                    try:
                        rel_sql = text("""
                            INSERT INTO post_collections (
                                post_id,
                                collection_id,
                                order_in_collection,
                                added_at
                            ) VALUES (
                                :post_id,
                                :collection_id,
                                :order_in_collection,
                                NOW()
                            )
                            ON CONFLICT (post_id, collection_id) DO UPDATE SET
                                order_in_collection = EXCLUDED.order_in_collection,
                                added_at = NOW()
                        """)

                        session.execute(rel_sql, {
                            'post_id': post_id,
                            'collection_id': collection_id,
                            'order_in_collection': order
                        })
                        session.commit()
                        stats['relationships_inserted'] += 1

                    except Exception as e:
                        logger.warning(f"    ⚠️  Could not insert relationship for post {post_id}: {e}")
                        stats['relationships_skipped'] += 1
                        session.rollback()
                        continue

            except Exception as e:
                logger.error(f"    ❌ Error saving collection {collection_id}: {e}")
                session.rollback()
                continue

        session.close()

        logger.info(f"  ✅ PostgreSQL save complete:")
        logger.info(f"     Collections: {stats['collections_inserted']} saved")
        logger.info(f"     Relationships: {stats['relationships_inserted']} saved")

    except Exception as e:
        logger.error(f"  ❌ PostgreSQL error: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# Original Functions
# ============================================================================

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

    logger.info(f"    📥 Attempting to download collection image from: {image_url[:80]}...")

    try:
        # Create directory structure
        images_dir = Path("data/media/collections") / creator_id
        logger.info(f"    📁 Creating directory: {images_dir.absolute()}")
        images_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"    ✅ Directory created/verified: {images_dir.absolute()}")

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
        logger.info(f"    💾 Saving to: {output_path.absolute()}")

        # Download image
        logger.info(f"    🌐 Downloading from Patreon...")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        image_size = len(response.content)
        logger.info(f"    📦 Downloaded {image_size} bytes")

        # Save to file
        output_path.write_bytes(response.content)
        logger.info(f"    ✅ File saved successfully")

        # Return relative path for JSON storage
        relative_path = f"collections/{creator_id}/{filename}"
        logger.info(f"    💾 Collection image saved: {relative_path}")

        return relative_path

    except Exception as e:
        logger.error(f"    ❌ Failed to download collection image: {e}")
        return None


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
            if collection_image:
                logger.info(f"  🖼️  Found image URL: {collection_image[:80]}...")
            else:
                logger.warning(f"  ⚠️  Found thumbnail element but imgurl attribute is empty")
        except NoSuchElementException:
            logger.warning(f"  ⚠️  No box-collection-thumbnail element found for collection")

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
                    # We need to go up until we find a parent that contains BOTH thumbnail and title
                    parent = link
                    for level in range(10):  # Increased range to go higher
                        parent = parent.find_element(By.XPATH, '..')
                        # Check if this parent contains BOTH the title AND thumbnail
                        try:
                            parent.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-title"]')
                            parent.find_element(By.CSS_SELECTOR, '[data-tag="box-collection-thumbnail"]')
                            collection_elements.append(parent)
                            logger.debug(f"  ✓ Found complete collection container at level {level}")
                            break
                        except NoSuchElementException:
                            continue

                logger.info(f"  ✓ Found {len(collection_elements)} collection card elements")

            except NoSuchElementException:
                logger.warning(f"  ⚠️  No collection elements found")
                continue

            # PHASE 1: Extract basic metadata from all collections WITHOUT navigating away
            # This prevents stale element references
            for element in collection_elements:
                collection_data = extract_collection_data(driver, element)
                if collection_data:
                    collections_data.append(collection_data)

            # If we found collections, break (don't try other URL format)
            if collections_data:
                logger.info(f"\n  📊 Extracted metadata for {len(collections_data)} collections")

                # PHASE 2: Now visit each collection to extract post IDs and download images
                logger.info(f"  🔄 Now extracting post IDs and downloading images...\n")
                for i, collection_data in enumerate(collections_data, 1):
                    logger.info(f"  [{i}/{len(collections_data)}] Processing: {collection_data['collection_name']}")

                    # Extract post IDs
                    post_ids = extract_post_ids_from_collection(driver, collection_data['collection_url'])
                    collection_data['post_ids'] = post_ids
                    collection_data['post_count'] = len(post_ids)  # Update with actual count

                    # Download collection image locally
                    if collection_data.get('collection_image'):
                        logger.info(f"  📸 Downloading image for collection {collection_data['collection_id']}")
                        local_path = download_collection_image(
                            collection_data['collection_image'],
                            creator_id,
                            collection_data['collection_id']
                        )
                        collection_data['collection_image_local'] = local_path
                        if local_path:
                            logger.info(f"  ✅ Image saved: {local_path}")
                        else:
                            logger.warning(f"  ⚠️  Image download failed for collection {collection_data['collection_id']}")
                    else:
                        logger.info(f"  ⚠️  No collection_image URL found for: {collection_data['collection_name']}")
                        collection_data['collection_image_local'] = None

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
    Save collections data to JSON file and PostgreSQL (if enabled)

    DUAL MODE:
    - Always saves to JSON (backward compatibility)
    - Also saves to PostgreSQL if config/use_postgresql.flag exists

    Args:
        creator_id: Creator identifier
        collections_data: Collections data dictionary
    """
    # Always save to JSON (backward compatibility)
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{creator_id}_collections.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(collections_data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Saved collections to JSON: {output_file}")

    # Also save to PostgreSQL if flag is enabled
    if use_postgresql():
        logger.info(f"🐘 PostgreSQL mode enabled - saving to database...")
        save_collections_to_postgres(creator_id, collections_data)
    else:
        logger.info(f"📝 PostgreSQL mode disabled (no flag found)")
        logger.info(f"   To enable: touch config/use_postgresql.flag")


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
    summary = {
        'total_creators': len(creators),
        'creators_with_collections': 0,
        'total_collections': 0,
        'total_posts_in_collections': 0,
        'details': []
    }

    for creator in creators:
        try:
            collections_data = scrape_collections_for_creator(auth, creator)

            if collections_data:
                save_collections_data(creator['creator_id'], collections_data)

                # Track statistics
                num_collections = len(collections_data['collections'])
                total_posts = sum(len(c['post_ids']) for c in collections_data['collections'])

                summary['creators_with_collections'] += 1
                summary['total_collections'] += num_collections
                summary['total_posts_in_collections'] += total_posts

                creator_detail = {
                    'creator_id': creator['creator_id'],
                    'creator_name': creator['name'],
                    'num_collections': num_collections,
                    'total_posts': total_posts,
                    'collections': [
                        {
                            'name': c['collection_name'],
                            'id': c['collection_id'],
                            'posts': len(c['post_ids'])
                        } for c in collections_data['collections']
                    ]
                }
                summary['details'].append(creator_detail)

                # Update posts if requested
                if args.update_posts:
                    update_posts_with_collections(creator['creator_id'])
            else:
                logger.warning(f"No collections data to save for {creator['name']}")
                summary['details'].append({
                    'creator_id': creator['creator_id'],
                    'creator_name': creator['name'],
                    'num_collections': 0,
                    'total_posts': 0,
                    'collections': []
                })

        except Exception as e:
            logger.error(f"❌ Error processing {creator['name']}: {e}")
            continue

    # Cleanup
    auth.close()

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("✅ Phase 3 Collections Scraping Complete!")
    logger.info("="*60)
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"  Creators processed: {summary['total_creators']}")
    logger.info(f"  Creators with collections: {summary['creators_with_collections']}")
    logger.info(f"  Total collections found: {summary['total_collections']}")
    logger.info(f"  Total posts in collections: {summary['total_posts_in_collections']}")

    if summary['details']:
        logger.info(f"\n📋 DETAILS:")
        for detail in summary['details']:
            if detail['num_collections'] > 0:
                logger.info(f"\n  🎨 {detail['creator_name']} ({detail['creator_id']})")
                logger.info(f"     Collections: {detail['num_collections']}")
                logger.info(f"     Total posts: {detail['total_posts']}")
                logger.info(f"     Collections found:")
                for col in detail['collections']:
                    logger.info(f"       - {col['name']} (ID: {col['id']}): {col['posts']} posts")

    logger.info("\n" + "="*60 + "\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
