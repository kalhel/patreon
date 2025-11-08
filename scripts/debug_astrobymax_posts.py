#!/usr/bin/env python3
"""
Quick diagnostic: Why does AstroByMax show 616 posts?
This script breaks down the posts by different statuses to understand the discrepancy.
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
    print("  🔍 AstroByMax Posts Diagnostic")
    print("=" * 80)
    print()

    # Connect
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # First, let's see the breakdown by deleted_at status
        print("📊 BREAKDOWN BY DELETED STATUS")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                CASE
                    WHEN deleted_at IS NULL THEN 'Active (not deleted)'
                    ELSE 'Deleted'
                END as status,
                COUNT(*) as count
            FROM posts
            WHERE creator_id = 'astrobymax'
            GROUP BY deleted_at IS NULL
            ORDER BY count DESC
        """))

        for row in result:
            print(f"  {row[0]:<30} {row[1]:>6} posts")
        print()

        # Now let's see if there are posts with NULL or empty content
        print("📊 BREAKDOWN BY CONTENT STATUS")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                CASE
                    WHEN full_content IS NULL OR full_content = '' THEN 'No content'
                    ELSE 'Has content'
                END as content_status,
                COUNT(*) as count
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND deleted_at IS NULL
            GROUP BY (full_content IS NULL OR full_content = '')
            ORDER BY count DESC
        """))

        for row in result:
            print(f"  {row[0]:<30} {row[1]:>6} posts")
        print()

        # Let's see the date range
        print("📊 DATE RANGE")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                MIN(created_at) as oldest_post,
                MAX(created_at) as newest_post,
                MIN(updated_at) as first_updated,
                MAX(updated_at) as last_updated
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND deleted_at IS NULL
        """))

        row = result.fetchone()
        if row:
            print(f"  Oldest post created:     {row[0]}")
            print(f"  Newest post created:     {row[1]}")
            print(f"  First updated:           {row[2]}")
            print(f"  Last updated:            {row[3]}")
        print()

        # Check scraping_status to see what we're tracking
        print("📊 SCRAPING STATUS (URLs being tracked)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                phase1_status,
                COUNT(*) as count
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
            WHERE cs.platform_id = 'astrobymax'
              AND cs.platform = 'patreon'
            GROUP BY phase1_status
            ORDER BY count DESC
        """))

        total_tracked = 0
        for row in result:
            print(f"  {row[0]:<30} {row[1]:>6} URLs")
            total_tracked += row[1]
        print(f"  {'TOTAL TRACKED URLs':<30} {total_tracked:>6}")
        print()

        # Final summary
        print("=" * 80)
        print("  📝 SUMMARY")
        print("=" * 80)

        result = conn.execute(text("""
            SELECT COUNT(*) FROM posts
            WHERE creator_id = 'astrobymax' AND deleted_at IS NULL
        """))
        active_posts = result.scalar()

        result = conn.execute(text("""
            SELECT COUNT(*) FROM posts
            WHERE creator_id = 'astrobymax' AND deleted_at IS NOT NULL
        """))
        deleted_posts = result.scalar()

        result = conn.execute(text("""
            SELECT COUNT(*) FROM posts
            WHERE creator_id = 'astrobymax'
        """))
        total_posts = result.scalar()

        print(f"\n  Active posts (deleted_at IS NULL):    {active_posts}")
        print(f"  Deleted posts (deleted_at IS NOT NULL): {deleted_posts}")
        print(f"  TOTAL posts in database:                {total_posts}")
        print()
        print("💡 EXPLANATION:")
        print("  - If you see many deleted posts, that's normal - the scraper marks")
        print("    posts as deleted when they're removed from Patreon")
        print("  - The web viewer should only show active posts (deleted_at IS NULL)")
        print("  - The scraping_status table shows how many URLs we're tracking")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
