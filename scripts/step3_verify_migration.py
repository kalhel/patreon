#!/usr/bin/env python3
"""
STEP 3: Verify schema v2 migration completed successfully

Checks:
1. All posts have source_id
2. All collections have source_id
3. Foreign keys are valid
4. No orphaned records
5. Data counts match expectations
"""

import os
import sys
from pathlib import Path
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
    print("  STEP 3: Verify Schema V2 Migration")
    print("=" * 80)
    print()

    # Connect
    print("🔌 Connecting to PostgreSQL...")
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    all_checks_passed = True

    with engine.connect() as conn:
        print("✅ Connected")
        print()

        # ====================================================================
        # CHECK 1: Posts table structure
        # ====================================================================
        print("🔍 CHECK 1: Posts table has source_id column")
        result = conn.execute(text("""
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = 'posts'
              AND column_name IN ('source_id', 'creator_id')
            ORDER BY column_name
        """))

        for row in result:
            print(f"  Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}")

        # Verify source_id exists and is NOT NULL
        result = conn.execute(text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'posts' AND column_name = 'source_id'
        """))
        row = result.fetchone()

        if row is None:
            print("  ❌ FAIL: source_id column missing!")
            all_checks_passed = False
        elif row[0] == 'YES':
            print("  ⚠️  WARNING: source_id is nullable (should be NOT NULL)")
            all_checks_passed = False
        else:
            print("  ✅ PASS: source_id exists and is NOT NULL")
        print()

        # ====================================================================
        # CHECK 2: Collections table structure
        # ====================================================================
        print("🔍 CHECK 2: Collections table has source_id column")
        result = conn.execute(text("""
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_name = 'collections'
              AND column_name IN ('source_id', 'creator_id')
            ORDER BY column_name
        """))

        for row in result:
            print(f"  Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}")

        # Verify source_id exists and is NOT NULL
        result = conn.execute(text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = 'collections' AND column_name = 'source_id'
        """))
        row = result.fetchone()

        if row is None:
            print("  ❌ FAIL: source_id column missing!")
            all_checks_passed = False
        elif row[0] == 'YES':
            print("  ⚠️  WARNING: source_id is nullable (should be NOT NULL)")
            all_checks_passed = False
        else:
            print("  ✅ PASS: source_id exists and is NOT NULL")
        print()

        # ====================================================================
        # CHECK 3: All posts have valid source_id
        # ====================================================================
        print("🔍 CHECK 3: All posts have valid source_id")

        # Count total posts
        result = conn.execute(text("SELECT COUNT(*) FROM posts"))
        total_posts = result.scalar()

        # Count posts with source_id
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM posts p
            JOIN creator_sources cs ON cs.id = p.source_id
        """))
        valid_posts = result.scalar()

        print(f"  Total posts: {total_posts}")
        print(f"  Posts with valid source_id: {valid_posts}")

        if total_posts == valid_posts:
            print("  ✅ PASS: All posts have valid source_id")
        else:
            print(f"  ❌ FAIL: {total_posts - valid_posts} posts missing valid source_id!")
            all_checks_passed = False
        print()

        # ====================================================================
        # CHECK 4: All collections have valid source_id
        # ====================================================================
        print("🔍 CHECK 4: All collections have valid source_id")

        # Count total collections
        result = conn.execute(text("SELECT COUNT(*) FROM collections"))
        total_collections = result.scalar()

        # Count collections with source_id
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM collections col
            JOIN creator_sources cs ON cs.id = col.source_id
        """))
        valid_collections = result.scalar()

        print(f"  Total collections: {total_collections}")
        print(f"  Collections with valid source_id: {valid_collections}")

        if total_collections == valid_collections:
            print("  ✅ PASS: All collections have valid source_id")
        else:
            print(f"  ❌ FAIL: {total_collections - valid_collections} collections missing valid source_id!")
            all_checks_passed = False
        print()

        # ====================================================================
        # CHECK 5: Distribution by creator
        # ====================================================================
        print("🔍 CHECK 5: Data distribution by creator")
        result = conn.execute(text("""
            SELECT
                c.name as creator_name,
                cs.platform,
                COALESCE(p.posts_count, 0) as posts_count,
                COALESCE(col.collections_count, 0) as collections_count
            FROM creators c
            JOIN creator_sources cs ON cs.creator_id = c.id
            LEFT JOIN (
                SELECT source_id, COUNT(*) as posts_count
                FROM posts
                GROUP BY source_id
            ) p ON p.source_id = cs.id
            LEFT JOIN (
                SELECT source_id, COUNT(*) as collections_count
                FROM collections
                GROUP BY source_id
            ) col ON col.source_id = cs.id
            ORDER BY c.name, cs.platform
        """))

        print(f"  {'Creator':<20} {'Platform':<10} {'Posts':<10} {'Collections':<15}")
        print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*15}")

        for row in result:
            print(f"  {row[0]:<20} {row[1]:<10} {row[2]:<10} {row[3]:<15}")

        print("  ✅ PASS: Distribution shown above")
        print()

        # ====================================================================
        # CHECK 6: scraping_status consistency
        # ====================================================================
        print("🔍 CHECK 6: scraping_status has valid source_id references")

        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
        """))
        valid_scraping_status = result.scalar()

        result = conn.execute(text("SELECT COUNT(*) FROM scraping_status"))
        total_scraping_status = result.scalar()

        print(f"  Total scraping_status: {total_scraping_status}")
        print(f"  With valid source_id: {valid_scraping_status}")

        if total_scraping_status == valid_scraping_status:
            print("  ✅ PASS: All scraping_status records have valid source_id")
        else:
            print(f"  ❌ FAIL: {total_scraping_status - valid_scraping_status} invalid references!")
            all_checks_passed = False
        print()

        # ====================================================================
        # FINAL RESULT
        # ====================================================================
        print("=" * 80)
        if all_checks_passed:
            print("  ✅ ALL CHECKS PASSED - Migration successful!")
            print("=" * 80)
            print()
            print("Next steps:")
            print("  1. Test the web viewer - verify posts and collections display correctly")
            print("  2. Run diagnostic script again to confirm data consistency")
            print("  3. Once confirmed, old creator_id columns can be dropped (optional)")
            print()
            return 0
        else:
            print("  ❌ SOME CHECKS FAILED - Review errors above")
            print("=" * 80)
            print()
            print("DO NOT proceed until all checks pass!")
            print()
            return 1


if __name__ == "__main__":
    sys.exit(main())
