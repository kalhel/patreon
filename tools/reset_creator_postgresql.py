#!/usr/bin/env python3
"""
Reset creator data from PostgreSQL (Schema V2)
Deletes all data for a creator from scraping_status, posts, and collections
Keeps the creator and creator_sources intact
"""

import os
import sys
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

load_dotenv()

def get_database_url():
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def main():
    print("=" * 80)
    print("  🔄 Reset Creator Data (PostgreSQL)")
    print("=" * 80)
    print()

    creator_id = input("Enter creator platform_id to reset (e.g., astrobymax): ").strip()

    if not creator_id:
        print("❌ No creator_id provided")
        return 1

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    # First, check what we're about to delete
    with engine.connect() as conn:
        # Get source_id
        result = conn.execute(text("""
            SELECT cs.id, c.name
            FROM creator_sources cs
            JOIN creators c ON c.id = cs.creator_id
            WHERE cs.platform_id = :creator_id
              AND cs.platform = 'patreon'
        """), {'creator_id': creator_id})

        row = result.fetchone()
        if not row:
            print(f"❌ Creator '{creator_id}' not found in database!")
            return 1

        source_id = row[0]
        creator_name = row[1]

        print(f"Creator: {creator_name}")
        print(f"Platform ID: {creator_id}")
        print(f"Source ID: {source_id}")
        print()

        # Count what will be deleted
        print("📊 Data to be deleted:")
        print("-" * 80)

        # Count scraping_status entries
        result = conn.execute(text("""
            SELECT COUNT(*) FROM scraping_status
            WHERE source_id = :source_id
        """), {'source_id': source_id})
        scraping_count = result.scalar()
        print(f"  scraping_status entries:  {scraping_count}")

        # Count posts
        result = conn.execute(text("""
            SELECT COUNT(*) FROM posts
            WHERE creator_id = :creator_id
        """), {'creator_id': creator_id})
        posts_count = result.scalar()
        print(f"  posts:                    {posts_count}")

        # Count collections
        result = conn.execute(text("""
            SELECT COUNT(*) FROM collections
            WHERE creator_id = :creator_id
        """), {'creator_id': creator_id})
        collections_count = result.scalar()
        print(f"  collections:              {collections_count}")

        print()

        if scraping_count == 0 and posts_count == 0 and collections_count == 0:
            print("✓ No data to delete - creator already clean")
            return 0

    # Confirm deletion
    print("⚠️  WARNING: This will PERMANENTLY delete all data for this creator!")
    print("The creator and source will remain, but all posts/collections will be deleted.")
    print()
    response = input("Are you sure you want to DELETE this data? (type 'DELETE' to confirm): ")

    if response != 'DELETE':
        print("❌ Aborted by user")
        return 0

    # Perform deletion in a transaction
    with engine.begin() as conn:
        print()
        print("🗑️  Deleting data...")
        print()

        # Delete from scraping_status
        result = conn.execute(text("""
            DELETE FROM scraping_status
            WHERE source_id = :source_id
        """), {'source_id': source_id})
        print(f"  ✅ Deleted {result.rowcount} entries from scraping_status")

        # Delete from posts
        result = conn.execute(text("""
            DELETE FROM posts
            WHERE creator_id = :creator_id
        """), {'creator_id': creator_id})
        print(f"  ✅ Deleted {result.rowcount} posts")

        # Delete from collections
        result = conn.execute(text("""
            DELETE FROM collections
            WHERE creator_id = :creator_id
        """), {'creator_id': creator_id})
        print(f"  ✅ Deleted {result.rowcount} collections")

        print()
        print("=" * 80)
        print("  ✅ RESET COMPLETE")
        print("=" * 80)
        print()
        print(f"Creator '{creator_name}' has been reset successfully.")
        print()
        print("Next steps to re-scrape:")
        print("  1. Run Phase 1 (URL collection):")
        print(f"     python3 src/phase1_url_collector.py --creator {creator_id}")
        print()
        print("  2. Run Phase 2 (Post details):")
        print(f"     python3 src/phase2_detail_extractor.py --creator {creator_id}")
        print()
        print("  3. Run Phase 3 (Collections):")
        print(f"     python3 src/phase3_collections_scraper.py --creator {creator_id}")
        print()
        print("  4. Verify in settings page that data looks correct")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
