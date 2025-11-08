#!/usr/bin/env python3
"""
Debug: Find the exact 3 missing posts between scraping_status and posts
"""

import os
import sys
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

load_dotenv()

def get_database_url():
    """Build PostgreSQL connection URL"""
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
    print("  🔍 Finding the 3 Missing Posts")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Get all post_ids from scraping_status
        print("📊 COMPARING scraping_status vs posts table")
        print("-" * 80)

        result = conn.execute(text("""
            SELECT
                ss.post_id,
                CASE WHEN p.id IS NULL THEN 'MISSING' ELSE 'EXISTS' END as in_posts,
                CASE WHEN p.deleted_at IS NULL THEN 'ACTIVE' ELSE 'DELETED' END as post_status
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
            LEFT JOIN posts p ON p.post_id = ss.post_id AND p.creator_id = 'astrobymax'
            WHERE cs.platform_id = 'astrobymax'
              AND cs.platform = 'patreon'
            ORDER BY ss.created_at DESC
        """))

        missing_posts = []
        deleted_posts = []
        active_posts = []

        for row in result:
            post_id = row[0]
            in_posts = row[1]
            post_status = row[2]

            if in_posts == 'MISSING':
                missing_posts.append(post_id)
            elif post_status == 'DELETED':
                deleted_posts.append(post_id)
            else:
                active_posts.append(post_id)

        print(f"  Post IDs in scraping_status:     {len(missing_posts) + len(deleted_posts) + len(active_posts)}")
        print(f"  Posts MISSING from posts table:  {len(missing_posts)}")
        print(f"  Posts DELETED in posts table:    {len(deleted_posts)}")
        print(f"  Posts ACTIVE in posts table:     {len(active_posts)}")
        print()

        if missing_posts:
            print("❌ MISSING POSTS (in scraping_status but not in posts table):")
            for post_id in missing_posts[:10]:
                print(f"  - {post_id}")
            print()

        if deleted_posts:
            print("🗑️  DELETED POSTS (in posts table with deleted_at set):")
            for post_id in deleted_posts[:10]:
                print(f"  - {post_id}")
            print()

        # Now check full_content status
        print("📊 CONTENT STATUS (for active posts)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN full_content IS NOT NULL AND full_content != '' THEN 1 END) as with_content,
                COUNT(CASE WHEN full_content IS NULL OR full_content = '' THEN 1 END) as without_content
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND deleted_at IS NULL
        """))

        row = result.fetchone()
        if row:
            print(f"  Total active posts:        {row[0]}")
            print(f"  Posts WITH full_content:   {row[1]}")
            print(f"  Posts WITHOUT full_content: {row[2]}")
        print()

        # Summary
        print("=" * 80)
        print("  💡 EXPLANATION")
        print("=" * 80)
        print()

        if len(missing_posts) == 3:
            print(f"✓ Found the 3 missing posts!")
            print(f"  They are in scraping_status but NOT in posts table")
            print(f"  These should be shown as 'pending' in Phase 1")
        elif len(deleted_posts) == 3:
            print(f"✓ Found the 3 'missing' posts!")
            print(f"  They are in posts table but marked as DELETED")
            print(f"  The scraper correctly marked them as deleted")
        elif len(missing_posts) + len(deleted_posts) == 3:
            print(f"✓ Found the 3 'missing' posts!")
            print(f"  {len(missing_posts)} are truly missing from posts table")
            print(f"  {len(deleted_posts)} are marked as deleted")
        else:
            print(f"⚠️  Unexpected result:")
            print(f"  Missing: {len(missing_posts)}, Deleted: {len(deleted_posts)}")
            print(f"  Expected total: 3, Got: {len(missing_posts) + len(deleted_posts)}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
