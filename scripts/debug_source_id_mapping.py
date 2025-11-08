#!/usr/bin/env python3
"""
Debug: Check source_id mapping for AstroByMax
Why does the verification script show 616 posts when we only have 77?
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
    print("  🔍 Source ID Mapping Diagnostic")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Check creator_sources for AstroByMax
        print("📊 CREATOR SOURCES for AstroByMax")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                cs.id as source_id,
                cs.platform,
                cs.platform_id,
                c.name as creator_name
            FROM creator_sources cs
            JOIN creators c ON c.id = cs.creator_id
            WHERE cs.platform_id = 'astrobymax'
               OR LOWER(c.name) LIKE '%astrobymax%'
            ORDER BY cs.id
        """))

        source_ids = []
        for row in result:
            print(f"  source_id: {row[0]}, platform: {row[1]}, platform_id: {row[2]}, creator: {row[3]}")
            source_ids.append(row[0])

        if not source_ids:
            print("  ❌ No creator_sources found for AstroByMax!")
            return 1

        print()

        # Now check posts by source_id
        print("📊 POSTS BY SOURCE_ID")
        print("-" * 80)
        for source_id in source_ids:
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active
                FROM posts
                WHERE source_id = :source_id
            """), {'source_id': source_id})

            row = result.fetchone()
            if row:
                print(f"  source_id {source_id}: {row[1]} active / {row[0]} total posts")

        print()

        # Check posts by creator_id (old schema v1)
        print("📊 POSTS BY CREATOR_ID (schema v1)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as active
            FROM posts
            WHERE creator_id = 'astrobymax'
        """))

        row = result.fetchone()
        if row:
            print(f"  creator_id 'astrobymax': {row[1]} active / {row[0]} total posts")

        print()

        # Check if there are posts with BOTH creator_id and source_id
        print("📊 POSTS WITH BOTH creator_id AND source_id")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as count
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND source_id IS NOT NULL
        """))

        count = result.scalar()
        print(f"  Posts with both creator_id='astrobymax' AND source_id: {count}")
        print()

        # Check the verification query (what step3 uses)
        print("📊 VERIFICATION QUERY (what step3_verify_migration.py uses)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                c.name as creator_name,
                cs.platform,
                COUNT(p.id) as posts_count
            FROM creators c
            JOIN creator_sources cs ON cs.creator_id = c.id
            LEFT JOIN posts p ON p.source_id = cs.id
            WHERE cs.platform_id = 'astrobymax'
            GROUP BY c.name, cs.platform
        """))

        for row in result:
            print(f"  {row[0]} ({row[1]}): {row[2]} posts")

        print()

        # Summary
        print("=" * 80)
        print("  💡 EXPLANATION")
        print("=" * 80)
        print()
        print("If the verification query shows more posts than creator_id query:")
        print("  → There might be duplicate source_ids or incorrect JOIN")
        print()
        print("If they match:")
        print("  → Migration is correct, verification script needs update")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
