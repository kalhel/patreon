#!/usr/bin/env python3
"""
Fix Creator Population Issue

The migration created only 1 "Unknown" creator, but we should have 4 creators
from config/creators.json. This script:

1. Reads config/creators.json
2. Creates the 4 creators in the creators table
3. Creates the 4 creator_sources (all Patreon platform)
4. Updates scraping_status to point to correct source_id based on firebase_data
"""

import os
import json
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def build_db_url():
    """Build database URL from environment variables"""
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in environment")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def load_creators_config():
    """Load creators from config/creators.json"""
    config_file = Path(__file__).parent / "config" / "creators.json"

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file, 'r') as f:
        data = json.load(f)

    return data['creators']


def main():
    print("=" * 70)
    print("  Fix Creator Population - Populate from config/creators.json")
    print("=" * 70)
    print()

    # Connect to database
    db_url = build_db_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    # Load creators configuration
    logger.info("📂 Loading creators from config/creators.json...")
    creators_config = load_creators_config()
    logger.info(f"   Found {len(creators_config)} creators in config")
    print()

    # Show current state
    logger.info("🔍 Checking current database state...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM creators"))
        current_count = result.scalar()
        logger.info(f"   Current creators in DB: {current_count}")

        result = conn.execute(text("SELECT COUNT(*) FROM creator_sources"))
        current_sources = result.scalar()
        logger.info(f"   Current creator_sources in DB: {current_sources}")

        result = conn.execute(text("SELECT COUNT(*) FROM scraping_status"))
        total_posts = result.scalar()
        logger.info(f"   Total posts in scraping_status: {total_posts}")
    print()

    # Ask for confirmation
    print("⚠️  This script will:")
    print("   1. DELETE the current 'Unknown' creator")
    print("   2. CREATE 4 new creators from config/creators.json")
    print("   3. CREATE 4 creator_sources (all Patreon)")
    print("   4. UPDATE scraping_status to point to correct source_id")
    print()

    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cancelled.")
        return
    print()

    # Step 1: Delete Unknown creator (will cascade to creator_sources)
    logger.info("🗑️  Step 1: Deleting 'Unknown' creator...")
    with engine.connect() as conn:
        result = conn.execute(text("DELETE FROM creators WHERE name = 'Unknown'"))
        conn.commit()
        logger.info(f"   ✅ Deleted {result.rowcount} creator(s)")
    print()

    # Step 2: Create creators from config
    logger.info("👤 Step 2: Creating creators from config...")
    creator_map = {}  # creator_id -> (new_creator_pk, source_pk)

    with engine.connect() as conn:
        for creator_config in creators_config:
            creator_id = creator_config['creator_id']  # e.g., "astrobymax"
            name = creator_config['name']  # e.g., "AstroByMax"
            avatar_filename = creator_config.get('avatar', '')

            # Insert creator (platform-agnostic)
            result = conn.execute(text("""
                INSERT INTO creators (name, avatar_filename, active)
                VALUES (:name, :avatar, true)
                RETURNING id
            """), {'name': name, 'avatar': avatar_filename})

            new_creator_pk = result.scalar()
            logger.info(f"   ✅ Created creator: {name} (id={new_creator_pk})")

            # Create creator_source (Patreon)
            patreon_url = creator_config.get('url', f"https://www.patreon.com/{creator_id}")

            result = conn.execute(text("""
                INSERT INTO creator_sources (
                    creator_id, platform, platform_id, platform_url,
                    platform_username, is_active, scraper_enabled
                ) VALUES (
                    :creator_id, 'patreon', :platform_id, :platform_url,
                    :username, true, true
                )
                RETURNING id
            """), {
                'creator_id': new_creator_pk,
                'platform_id': creator_id,
                'platform_url': patreon_url,
                'username': creator_id
            })

            new_source_pk = result.scalar()
            logger.info(f"      → Created Patreon source (source_id={new_source_pk})")

            # Store mapping: firebase creator_id -> source_id
            creator_map[creator_id] = {
                'creator_pk': new_creator_pk,
                'source_pk': new_source_pk,
                'name': name
            }

        conn.commit()
    print()

    # Step 3: Update scraping_status
    logger.info("📝 Step 3: Updating scraping_status.source_id based on firebase_data...")

    with engine.connect() as conn:
        # Get all posts with their firebase creator_id
        result = conn.execute(text("""
            SELECT id, post_id, firebase_data->>'creator_id' as firebase_creator_id
            FROM scraping_status
            WHERE firebase_data IS NOT NULL
        """))

        posts = result.fetchall()
        logger.info(f"   Found {len(posts)} posts with firebase_data")

        updated_count = 0
        unknown_count = 0

        for post in posts:
            post_pk = post[0]
            post_id = post[1]
            firebase_creator_id = post[2]

            # Find corresponding source_id
            if firebase_creator_id in creator_map:
                source_id = creator_map[firebase_creator_id]['source_pk']

                # Update scraping_status
                conn.execute(text("""
                    UPDATE scraping_status
                    SET source_id = :source_id
                    WHERE id = :post_pk
                """), {'source_id': source_id, 'post_pk': post_pk})

                updated_count += 1
            else:
                logger.warning(f"   ⚠️  Unknown creator_id in firebase_data: {firebase_creator_id} (post_id={post_id})")
                unknown_count += 1

        conn.commit()

        logger.info(f"   ✅ Updated {updated_count} posts")
        if unknown_count > 0:
            logger.warning(f"   ⚠️  {unknown_count} posts with unknown creator_id")
    print()

    # Step 4: Verify
    logger.info("✅ Step 4: Verification...")
    with engine.connect() as conn:
        # Count creators
        result = conn.execute(text("SELECT COUNT(*) FROM creators"))
        logger.info(f"   Total creators: {result.scalar()}")

        # Count sources
        result = conn.execute(text("SELECT COUNT(*) FROM creator_sources"))
        logger.info(f"   Total creator_sources: {result.scalar()}")

        # Posts per creator
        result = conn.execute(text("""
            SELECT
                c.name,
                COUNT(ss.id) as post_count
            FROM creators c
            JOIN creator_sources cs ON cs.creator_id = c.id
            LEFT JOIN scraping_status ss ON ss.source_id = cs.id
            GROUP BY c.name
            ORDER BY c.name
        """))

        print()
        logger.info("   Posts per creator:")
        for row in result.fetchall():
            logger.info(f"      • {row[0]}: {row[1]} posts")

    print()
    print("=" * 70)
    print("✅ Creator population fixed!")
    print("=" * 70)
    print()
    print("Next: Run 'bash check_creators.sh' to verify")


if __name__ == "__main__":
    main()
