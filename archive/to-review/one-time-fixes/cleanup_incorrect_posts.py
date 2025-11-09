#!/usr/bin/env python3
"""
Clean up posts that were incorrectly attributed to the wrong creator
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
    print("  🧹 Clean Up Incorrectly Attributed Posts")
    print("=" * 80)
    print()

    # Known incorrect posts for astrobymax
    # User verified these on Patreon and they belong to other creators
    incorrect_posts = {
        'astrobymax': ['96097452', '77933294', '42294201']
    }

    creator_id = input("Enter creator platform_id (default: astrobymax): ").strip() or "astrobymax"

    if creator_id not in incorrect_posts:
        print(f"No known incorrect posts for {creator_id}")
        print("Please edit this script to add the post IDs to clean up")
        return 0

    posts_to_delete = incorrect_posts[creator_id]

    print(f"Posts to DELETE from scraping_status for '{creator_id}':")
    for post_id in posts_to_delete:
        print(f"  - {post_id} (https://www.patreon.com/posts/{post_id})")
    print()

    print("⚠️  WARNING: This will permanently delete these records!")
    print("These posts will be removed from scraping_status and posts tables.")
    print()

    response = input("Are you sure you want to DELETE these posts? (type 'DELETE' to confirm): ")
    if response != 'DELETE':
        print("Aborted by user")
        return 0

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.begin() as conn:
        print()
        print("🧹 Deleting posts...")

        # First, get the source_id for this creator
        result = conn.execute(text("""
            SELECT cs.id
            FROM creator_sources cs
            WHERE cs.platform_id = :creator_id
              AND cs.platform = 'patreon'
        """), {'creator_id': creator_id})

        row = result.fetchone()
        if not row:
            print(f"❌ Creator '{creator_id}' not found in database!")
            return 1

        source_id = row[0]

        for post_id in posts_to_delete:
            # Delete from posts table (if exists)
            result = conn.execute(text("""
                DELETE FROM posts
                WHERE post_id = :post_id
                  AND creator_id = :creator_id
                RETURNING id
            """), {'post_id': post_id, 'creator_id': creator_id})

            if result.rowcount > 0:
                print(f"  ✅ Deleted {post_id} from posts table")
            else:
                print(f"  ℹ️  {post_id} not in posts table (expected)")

            # Delete from scraping_status
            result = conn.execute(text("""
                DELETE FROM scraping_status
                WHERE post_id = :post_id
                  AND source_id = :source_id
                RETURNING id
            """), {'post_id': post_id, 'source_id': source_id})

            if result.rowcount > 0:
                print(f"  ✅ Deleted {post_id} from scraping_status")
            else:
                print(f"  ⚠️  {post_id} not found in scraping_status!")

        print()
        print("=" * 80)
        print("  ✅ CLEANUP COMPLETE")
        print("=" * 80)
        print()
        print(f"Deleted {len(posts_to_delete)} incorrect posts from database.")
        print()
        print("Next steps:")
        print("  1. Verify in settings page that counts are now correct")
        print("  2. The Phase 1 bug needs to be fixed to prevent this in future")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
