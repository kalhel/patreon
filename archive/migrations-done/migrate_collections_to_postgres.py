#!/usr/bin/env python3
"""
Collections Migrator - Migrate Patreon collections from JSON to PostgreSQL

This script migrates collection data from JSON files to PostgreSQL database:
- Collections metadata (collections table)
- Post-Collection relationships (post_collections table)

Usage:
    python src/migrate_collections_to_postgres.py [options]

Options:
    --skip-checks     Skip pre-flight validation checks
    --yes, -y         Auto-confirm without prompting
    --file FILE       Migrate specific JSON file only
    --dry-run         Show what would be migrated without making changes

Examples:
    # Full migration with checks
    python src/migrate_collections_to_postgres.py

    # Skip checks and auto-confirm
    python src/migrate_collections_to_postgres.py --skip-checks --yes

    # Migrate single file
    python src/migrate_collections_to_postgres.py --file data/backups/headonhistory_20251106_070558/headonhistory_collections.json
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class CollectionMigrator:
    """Migrate collections from JSON to PostgreSQL"""

    def __init__(self):
        """Initialize database connection"""
        try:
            database_url = self._get_database_url()
            self.engine = create_engine(database_url, echo=False)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("✅ Database connection initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise

    def _get_database_url(self) -> str:
        """Construct PostgreSQL connection URL from environment variables"""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME', 'alejandria')

        if not db_password:
            raise ValueError("DB_PASSWORD not found in environment")

        encoded_password = quote_plus(db_password)
        return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

    def preflight_checks(self) -> bool:
        """
        Run comprehensive pre-flight checks before migration

        Returns:
            True if all checks pass, False otherwise
        """
        logger.info("🔍 Running pre-flight checks...")

        all_passed = True

        # Check 1: Database connection
        logger.info("  ✓ Checking database connection...")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"    ✅ Connected to PostgreSQL: {version.split(',')[0]}")
        except Exception as e:
            logger.error(f"    ❌ Database connection failed: {e}")
            all_passed = False

        # Check 2: Collections tables exist
        logger.info("  ✓ Checking collections tables...")
        try:
            session = self.Session()
            result = session.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name IN ('collections', 'post_collections')
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            session.close()

            if 'collections' in tables and 'post_collections' in tables:
                logger.info("    ✅ Collections tables exist")
            else:
                missing = [t for t in ['collections', 'post_collections'] if t not in tables]
                logger.error(f"    ❌ Missing tables: {missing}")
                logger.error("       Run: psql $DATABASE_URL -f database/schema_posts.sql")
                all_passed = False
        except Exception as e:
            logger.error(f"    ❌ Error checking tables: {e}")
            all_passed = False

        # Check 3: JSON files exist
        logger.info("  ✓ Checking for collections JSON files...")
        json_files = self.find_json_files()
        if not json_files:
            logger.warning("    ⚠️  No collections JSON files found")
            logger.info("       Searched in: data/processed, data/backups, data/raw")
        else:
            logger.info(f"    ✅ Found {len(json_files)} collections JSON files")

            # Validate JSON structure
            logger.info("  ✓ Validating JSON structure...")
            valid_count = 0
            for json_file in json_files[:3]:  # Check first 3 files
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    if 'creator_id' in data and 'collections' in data:
                        if isinstance(data['collections'], list):
                            valid_count += 1
                        else:
                            logger.warning(f"    ⚠️  {json_file.name}: 'collections' is not a list")
                    else:
                        logger.warning(f"    ⚠️  {json_file.name}: missing 'creator_id' or 'collections'")
                except Exception as e:
                    logger.error(f"    ❌ Error reading {json_file.name}: {e}")

            if valid_count > 0:
                logger.info(f"    ✅ JSON structure validation passed ({valid_count} files checked)")

        # Check 4: Posts table exists (for foreign key)
        logger.info("  ✓ Checking posts table...")
        try:
            session = self.Session()
            result = session.execute(text("SELECT COUNT(*) FROM posts"))
            post_count = result.scalar()
            if post_count > 0:
                logger.info(f"    ✅ Posts table has {post_count} posts")
            else:
                logger.warning("    ⚠️  Posts table is empty")
                logger.warning("       Run: python src/migrate_json_to_postgres.py first")
            session.close()
        except Exception as e:
            logger.error(f"    ❌ Posts table check failed: {e}")
            all_passed = False

        # Check 5: Existing collections in database
        logger.info("  ✓ Checking for existing collections...")
        try:
            session = self.Session()
            result = session.execute(text("SELECT COUNT(*) FROM collections"))
            existing_count = result.scalar()
            if existing_count > 0:
                logger.warning(f"    ⚠️  Database already has {existing_count} collections")
                logger.warning(f"       Duplicates will be skipped, existing won't be overwritten")
            else:
                logger.info("    ✅ Collections table is empty")
            session.close()
        except Exception as e:
            logger.warning(f"    ⚠️  Could not check existing collections: {e}")

        # Summary
        logger.info("\n" + "="*60)
        if all_passed:
            logger.info("✅ ALL PRE-FLIGHT CHECKS PASSED")
        else:
            logger.error("❌ SOME PRE-FLIGHT CHECKS FAILED")
            logger.error("   Please fix the issues above before proceeding")
        logger.info("="*60 + "\n")

        return all_passed

    def find_json_files(self, search_paths: List[str] = None) -> List[Path]:
        """Find all *_collections.json files"""
        if search_paths is None:
            search_paths = ['data/processed', 'data/backups', 'data/raw']

        json_files = []
        for search_path in search_paths:
            path = Path(search_path)
            if path.exists():
                # Find all *_collections.json files recursively
                files = list(path.rglob('*_collections.json'))
                json_files.extend(files)
                logger.info(f"📁 Found {len(files)} collections files in {search_path}")

        logger.info(f"📊 Total collections files found: {len(json_files)}")
        return json_files

    def parse_timestamp(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime"""
        if not ts_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except:
            try:
                # Try date only (YYYY-MM-DD)
                return datetime.strptime(ts_str, '%Y-%m-%d')
            except:
                return None

    def migrate_collection(self, collection_data: Dict, creator_id: str, session) -> bool:
        """
        Migrate a single collection to PostgreSQL

        Returns:
            True if inserted, False if skipped (already exists)
        """
        collection_id = collection_data.get('collection_id')
        if not collection_id:
            logger.warning("⚠️ Collection without collection_id, skipping")
            return False

        try:
            # Check if collection already exists
            result = session.execute(
                text("SELECT 1 FROM collections WHERE collection_id = :collection_id"),
                {"collection_id": collection_id}
            )
            if result.fetchone():
                logger.debug(f"⏭️ Collection {collection_id} already exists, skipping")
                return False

            # Insert collection
            insert_sql = text("""
                INSERT INTO collections (
                    collection_id,
                    creator_id,
                    title,
                    description,
                    collection_url,
                    post_count,
                    scraped_at,
                    created_at
                ) VALUES (
                    :collection_id,
                    :creator_id,
                    :title,
                    :description,
                    :collection_url,
                    :post_count,
                    :scraped_at,
                    NOW()
                )
            """)

            session.execute(insert_sql, {
                'collection_id': collection_id,
                'creator_id': creator_id,
                'title': collection_data.get('collection_name', 'Unnamed Collection'),
                'description': collection_data.get('description'),
                'collection_url': collection_data.get('collection_url'),
                'post_count': collection_data.get('post_count', 0),
                'scraped_at': self.parse_timestamp(collection_data.get('scraped_at'))
            })

            # Insert post-collection relationships
            post_ids = collection_data.get('post_ids', [])
            relationships_inserted = 0

            for order, post_id in enumerate(post_ids, start=1):
                try:
                    # Check if post exists in posts table
                    result = session.execute(
                        text("SELECT 1 FROM posts WHERE post_id = :post_id"),
                        {"post_id": post_id}
                    )
                    if not result.fetchone():
                        logger.warning(f"  ⚠️  Post {post_id} not found in posts table, skipping relationship")
                        continue

                    # Insert relationship
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
                        ON CONFLICT (post_id, collection_id) DO NOTHING
                    """)

                    session.execute(rel_sql, {
                        'post_id': post_id,
                        'collection_id': collection_id,
                        'order_in_collection': order
                    })
                    relationships_inserted += 1

                except Exception as e:
                    logger.warning(f"  ⚠️  Error inserting relationship for post {post_id}: {e}")

            session.commit()
            logger.debug(f"✅ Inserted collection {collection_id} with {relationships_inserted} posts")
            return True

        except IntegrityError as e:
            session.rollback()
            logger.debug(f"⏭️ Collection {collection_id} already exists (integrity error)")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error migrating collection {collection_id}: {e}")
            return False

    def migrate_file(self, json_file: Path, dry_run: bool = False) -> Dict[str, int]:
        """
        Migrate collections from a single JSON file

        Returns:
            Dictionary with statistics: {inserted, skipped, errors}
        """
        logger.info(f"📦 Processing: {json_file}")

        stats = {
            'inserted': 0,
            'skipped': 0,
            'errors': 0,
            'relationships': 0
        }

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            creator_id = data.get('creator_id')
            collections = data.get('collections', [])

            if not creator_id:
                logger.error(f"❌ No creator_id in {json_file}, skipping")
                stats['errors'] = 1
                return stats

            logger.info(f"   Creator: {creator_id}, Collections: {len(collections)}")

            if dry_run:
                logger.info(f"   🔍 DRY RUN: Would migrate {len(collections)} collections")
                return stats

            session = self.Session()

            for collection in collections:
                if self.migrate_collection(collection, creator_id, session):
                    stats['inserted'] += 1
                else:
                    stats['skipped'] += 1

            session.close()

            logger.info(f"✅ {json_file.name}: inserted={stats['inserted']}, "
                       f"skipped={stats['skipped']}")

        except Exception as e:
            logger.error(f"❌ Error processing {json_file}: {e}")
            stats['errors'] = 1

        return stats

    def migrate_all(self, skip_checks: bool = False, dry_run: bool = False):
        """Migrate all collections from JSON files to PostgreSQL"""
        logger.info("🚀 Starting collections migration from JSON to PostgreSQL")

        # Run pre-flight checks first
        if not skip_checks:
            if not self.preflight_checks():
                logger.error("❌ Pre-flight checks failed, aborting migration")
                logger.error("   Fix the issues above or use --skip-checks to bypass")
                return

            # Ask for confirmation
            logger.info("⚠️  Ready to migrate collections. This will:")
            logger.info("   1. Insert collections into PostgreSQL collections table")
            logger.info("   2. Create post-collection relationships")
            logger.info("   3. Skip duplicates (existing collection_ids won't be modified)")
            response = input("\n👉 Proceed with migration? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                logger.info("❌ Migration cancelled by user")
                return

        # Find all JSON files
        json_files = self.find_json_files()

        if not json_files:
            logger.error("❌ No collections JSON files found")
            return

        # Migrate each file
        total_stats = {
            'inserted': 0,
            'skipped': 0,
            'errors': 0
        }

        logger.info(f"\n📊 Migrating {len(json_files)} files...\n")

        for json_file in json_files:
            stats = self.migrate_file(json_file, dry_run=dry_run)
            total_stats['inserted'] += stats['inserted']
            total_stats['skipped'] += stats['skipped']
            total_stats['errors'] += stats['errors']

        # Final summary
        logger.info("\n" + "="*60)
        logger.info("✅ MIGRATION COMPLETE!")
        logger.info(f"📊 Total inserted: {total_stats['inserted']}")
        logger.info(f"⏭️  Total skipped:  {total_stats['skipped']}")
        logger.info(f"❌ Total errors:   {total_stats['errors']}")
        logger.info("="*60)

        # Show database stats
        self.show_stats()

    def show_stats(self):
        """Show collection statistics from database"""
        try:
            session = self.Session()

            # Total collections
            result = session.execute(text("SELECT COUNT(*) FROM collections"))
            total_collections = result.scalar()

            # Collections per creator
            result = session.execute(text("""
                SELECT creator_id, COUNT(*) as count
                FROM collections
                GROUP BY creator_id
                ORDER BY count DESC
            """))
            creators = result.fetchall()

            # Total relationships
            result = session.execute(text("SELECT COUNT(*) FROM post_collections"))
            total_relationships = result.scalar()

            session.close()

            logger.info("\n📊 DATABASE STATISTICS:")
            logger.info(f"   Total collections: {total_collections}")
            logger.info(f"   Total post-collection relationships: {total_relationships}")
            logger.info("\n👥 Collections per creator:")
            for creator_id, count in creators:
                logger.info(f"   - {creator_id}: {count} collections")

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate Patreon collections from JSON to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full migration with pre-flight checks
  python src/migrate_collections_to_postgres.py

  # Skip checks and confirmation (use with caution!)
  python src/migrate_collections_to_postgres.py --skip-checks --yes

  # Dry run (show what would be migrated)
  python src/migrate_collections_to_postgres.py --dry-run

  # Migrate specific file
  python src/migrate_collections_to_postgres.py --file data/backups/headonhistory_20251106_070558/headonhistory_collections.json
        """
    )
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip pre-flight checks (not recommended)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm (skip confirmation prompt)')
    parser.add_argument('--file', type=str,
                       help='Migrate specific JSON file instead of all')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')

    args = parser.parse_args()

    try:
        migrator = CollectionMigrator()

        if args.file:
            # Migrate single file
            logger.info(f"📦 Migrating single file: {args.file}")
            stats = migrator.migrate_file(Path(args.file), dry_run=args.dry_run)
            logger.info(f"✅ Done: inserted={stats['inserted']}, skipped={stats['skipped']}")
        else:
            # Migrate all files
            # Handle --yes flag by monkey-patching input
            if args.yes:
                import builtins
                builtins.input = lambda _: "yes"

            migrator.migrate_all(
                skip_checks=args.skip_checks,
                dry_run=args.dry_run
            )

    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
