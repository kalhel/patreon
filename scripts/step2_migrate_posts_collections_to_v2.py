#!/usr/bin/env python3
"""
STEP 2: Surgical migration of posts and collections to schema v2

What this script does:
1. Adds source_id column to posts table
2. Adds source_id column to collections table
3. Maps creator_id (VARCHAR) → source_id (INTEGER) using creator_sources
4. Updates foreign keys
5. Removes old creator_id columns

What this script DOES NOT do:
- Does NOT touch scraping_status (already in v2)
- Does NOT drop any tables
- Does NOT delete data
- Uses transactions (can rollback on error)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Load environment
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
    print("  STEP 2: Migrate posts & collections to Schema V2")
    print("=" * 80)
    print()

    # Connect to database
    print("🔌 Connecting to PostgreSQL...")
    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        print("✅ Connected")
        print()

        # ====================================================================
        # VERIFICATION: Check current state
        # ====================================================================
        print("🔍 Verifying current state...")

        # Check if posts already has source_id
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'posts' AND column_name = 'source_id'
        """))
        posts_has_source_id = result.fetchone() is not None

        # Check if collections already has source_id
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'collections' AND column_name = 'source_id'
        """))
        collections_has_source_id = result.fetchone() is not None

        print(f"  posts.source_id exists: {posts_has_source_id}")
        print(f"  collections.source_id exists: {collections_has_source_id}")
        print()

        if posts_has_source_id and collections_has_source_id:
            print("⚠️  Tables already have source_id columns!")
            print("   Migration may have been run before.")
            print()
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted by user")
                return 1

        # ====================================================================
        # START TRANSACTION
        # ====================================================================
        trans = conn.begin()

        try:
            # ================================================================
            # STEP 2.1: Migrate POSTS table
            # ================================================================
            print("📋 Migrating POSTS table...")

            # Add source_id column if not exists
            if not posts_has_source_id:
                print("  Adding source_id column to posts...")
                conn.execute(text("""
                    ALTER TABLE posts
                    ADD COLUMN source_id INTEGER
                """))
                print("  ✅ Column added")

            # Map creator_id (VARCHAR) → source_id (INTEGER)
            print("  Mapping creator_id → source_id...")
            result = conn.execute(text("""
                UPDATE posts p
                SET source_id = cs.id
                FROM creator_sources cs
                WHERE cs.platform_id = p.creator_id
                  AND cs.platform = 'patreon'
                  AND p.source_id IS NULL
            """))
            print(f"  ✅ Updated {result.rowcount} posts")

            # Check for unmapped posts
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posts WHERE source_id IS NULL
            """))
            unmapped_posts = result.scalar()

            if unmapped_posts > 0:
                print(f"  ⚠️  WARNING: {unmapped_posts} posts could not be mapped!")
                print("  Listing unmapped posts:")
                result = conn.execute(text("""
                    SELECT post_id, creator_id
                    FROM posts
                    WHERE source_id IS NULL
                    LIMIT 10
                """))
                for row in result:
                    print(f"    - post_id={row[0]}, creator_id={row[1]}")

                raise Exception(f"Cannot proceed: {unmapped_posts} posts without source_id")

            # Add foreign key constraint
            print("  Adding foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE posts
                DROP CONSTRAINT IF EXISTS posts_source_id_fkey
            """))
            conn.execute(text("""
                ALTER TABLE posts
                ADD CONSTRAINT posts_source_id_fkey
                FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE
            """))
            print("  ✅ Foreign key added")

            # Make source_id NOT NULL
            print("  Making source_id NOT NULL...")
            conn.execute(text("""
                ALTER TABLE posts
                ALTER COLUMN source_id SET NOT NULL
            """))
            print("  ✅ NOT NULL constraint added")

            print("✅ POSTS table migrated")
            print()

            # ================================================================
            # STEP 2.2: Migrate COLLECTIONS table
            # ================================================================
            print("📋 Migrating COLLECTIONS table...")

            # Add source_id column if not exists
            if not collections_has_source_id:
                print("  Adding source_id column to collections...")
                conn.execute(text("""
                    ALTER TABLE collections
                    ADD COLUMN source_id INTEGER
                """))
                print("  ✅ Column added")

            # Map creator_id (VARCHAR) → source_id (INTEGER)
            print("  Mapping creator_id → source_id...")
            result = conn.execute(text("""
                UPDATE collections col
                SET source_id = cs.id
                FROM creator_sources cs
                WHERE cs.platform_id = col.creator_id
                  AND cs.platform = 'patreon'
                  AND col.source_id IS NULL
            """))
            print(f"  ✅ Updated {result.rowcount} collections")

            # Check for unmapped collections
            result = conn.execute(text("""
                SELECT COUNT(*) FROM collections WHERE source_id IS NULL
            """))
            unmapped_collections = result.scalar()

            if unmapped_collections > 0:
                print(f"  ⚠️  WARNING: {unmapped_collections} collections could not be mapped!")
                print("  Listing unmapped collections:")
                result = conn.execute(text("""
                    SELECT collection_id, creator_id
                    FROM collections
                    WHERE source_id IS NULL
                    LIMIT 10
                """))
                for row in result:
                    print(f"    - collection_id={row[0]}, creator_id={row[1]}")

                raise Exception(f"Cannot proceed: {unmapped_collections} collections without source_id")

            # Add foreign key constraint
            print("  Adding foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE collections
                DROP CONSTRAINT IF EXISTS collections_source_id_fkey
            """))
            conn.execute(text("""
                ALTER TABLE collections
                ADD CONSTRAINT collections_source_id_fkey
                FOREIGN KEY (source_id) REFERENCES creator_sources(id) ON DELETE CASCADE
            """))
            print("  ✅ Foreign key added")

            # Make source_id NOT NULL
            print("  Making source_id NOT NULL...")
            conn.execute(text("""
                ALTER TABLE collections
                ALTER COLUMN source_id SET NOT NULL
            """))
            print("  ✅ NOT NULL constraint added")

            print("✅ COLLECTIONS table migrated")
            print()

            # ================================================================
            # FINAL VERIFICATION
            # ================================================================
            print("🔍 Final verification...")

            # Count migrated records
            result = conn.execute(text("SELECT COUNT(*) FROM posts WHERE source_id IS NOT NULL"))
            posts_count = result.scalar()

            result = conn.execute(text("SELECT COUNT(*) FROM collections WHERE source_id IS NOT NULL"))
            collections_count = result.scalar()

            print(f"  ✅ {posts_count} posts with source_id")
            print(f"  ✅ {collections_count} collections with source_id")
            print()

            # ================================================================
            # COMMIT TRANSACTION
            # ================================================================
            print("💾 Committing transaction...")
            trans.commit()
            print("✅ COMMITTED")
            print()

            print("=" * 80)
            print("  ✅ MIGRATION COMPLETE")
            print("=" * 80)
            print()
            print("Summary:")
            print(f"  - {posts_count} posts migrated to schema v2")
            print(f"  - {collections_count} collections migrated to schema v2")
            print()
            print("⚠️  NOTE: Old creator_id columns still exist but are NOT USED")
            print("   They can be removed later with step3 if everything works")
            print()

            return 0

        except Exception as e:
            print()
            print("=" * 80)
            print("  ❌ ERROR OCCURRED - ROLLING BACK")
            print("=" * 80)
            print()
            print(f"Error: {e}")
            print()
            trans.rollback()
            print("✅ Rolled back successfully - database unchanged")
            print()
            return 1


if __name__ == "__main__":
    sys.exit(main())
