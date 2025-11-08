#!/usr/bin/env python3
"""
Debug: Check Phase 1 status breakdown for AstroByMax
Should have 80 URLs: some completed, some pending
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
    print("  🔍 Phase 1 Status Breakdown - AstroByMax")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Check Phase 1 status breakdown
        print("📊 PHASE 1 STATUS (scraping_status table)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                ss.phase1_status,
                COUNT(*) as count
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
            WHERE cs.platform_id = 'astrobymax'
              AND cs.platform = 'patreon'
            GROUP BY ss.phase1_status
            ORDER BY count DESC
        """))

        total_urls = 0
        for row in result:
            print(f"  {row[0]:<20} {row[1]:>6} URLs")
            total_urls += row[1]

        print(f"  {'TOTAL':<20} {total_urls:>6} URLs")
        print()

        # Check which URLs don't have corresponding posts
        print("📊 URLs WITHOUT POSTS in posts table")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                ss.url,
                ss.phase1_status,
                ss.created_at
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
            LEFT JOIN posts p ON p.post_id = ss.post_id
            WHERE cs.platform_id = 'astrobymax'
              AND cs.platform = 'patreon'
              AND p.id IS NULL
            ORDER BY ss.created_at DESC
            LIMIT 10
        """))

        missing_count = 0
        for row in result:
            print(f"  URL: {row[0]}")
            print(f"    Status: {row[1]}, Created: {row[2]}")
            print()
            missing_count += 1

        if missing_count == 0:
            print("  ✅ All URLs have corresponding posts!")
        else:
            print(f"  ⚠️  Found {missing_count} URLs without posts")
        print()

        # Check posts that exist
        print("📊 POSTS IN posts TABLE")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active,
                COUNT(CASE WHEN full_content IS NOT NULL AND full_content != '' THEN 1 END) as with_content
            FROM posts
            WHERE creator_id = 'astrobymax'
        """))

        row = result.fetchone()
        if row:
            print(f"  Total posts in table:          {row[0]}")
            print(f"  Active posts (not deleted):    {row[1]}")
            print(f"  Posts with full_content:       {row[2]}")
        print()

        # Summary
        print("=" * 80)
        print("  💡 SUMMARY")
        print("=" * 80)
        print()
        print(f"Phase 1 (scraping_status):  {total_urls} URLs tracked")

        # Re-query for summary
        result = conn.execute(text("""
            SELECT COUNT(*) FROM posts WHERE creator_id = 'astrobymax' AND deleted_at IS NULL
        """))
        active_posts = result.scalar()

        print(f"Phase 2 (posts table):       {active_posts} active posts")
        print(f"Missing:                     {total_urls - active_posts} posts")
        print()

        if total_urls - active_posts > 0:
            print("⚠️  These missing posts should be shown as 'pending' in Phase 1")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
