#!/usr/bin/env python3
"""
Migrate posts from JSON files to PostgreSQL
Reads all *_posts_detailed.json files and inserts into posts table
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostMigrator:
    """Migrate posts from JSON to PostgreSQL"""

    def __init__(self):
        """Initialize database connection"""
        db_url = self._build_db_url_from_env()
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("🐘 Connected to PostgreSQL")

    def _build_db_url_from_env(self) -> str:
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

        # Check 2: Schema file exists
        logger.info("  ✓ Checking schema file...")
        schema_file = Path('database/schema_posts.sql')
        if not schema_file.exists():
            logger.error(f"    ❌ Schema file not found: {schema_file}")
            all_passed = False
        else:
            logger.info(f"    ✅ Schema file found: {schema_file}")

        # Check 3: JSON files exist
        logger.info("  ✓ Checking for JSON files...")
        json_files = self.find_json_files()
        if not json_files:
            logger.error("    ❌ No JSON files found in data/processed or data/backups")
            all_passed = False
        else:
            logger.info(f"    ✅ Found {len(json_files)} JSON files")

            # Validate JSON structure
            logger.info("  ✓ Validating JSON structure...")
            valid_count = 0
            for json_file in json_files[:3]:  # Check first 3 files
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        # Check if posts have required fields
                        sample = data[0]
                        required_fields = ['post_id', 'creator_id', 'post_url']
                        missing = [f for f in required_fields if f not in sample]
                        if missing:
                            logger.warning(f"    ⚠️  {json_file.name} missing fields: {missing}")
                        else:
                            valid_count += 1
                    else:
                        logger.warning(f"    ⚠️  {json_file.name} is not a list or is empty")
                except Exception as e:
                    logger.error(f"    ❌ Error reading {json_file.name}: {e}")

            if valid_count > 0:
                logger.info(f"    ✅ JSON structure validation passed ({valid_count} files checked)")
            else:
                logger.error("    ❌ No valid JSON files found")
                all_passed = False

        # Check 4: Disk space (estimate needed space)
        logger.info("  ✓ Checking disk space...")
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024**3)
            if free_gb < 1:
                logger.warning(f"    ⚠️  Low disk space: {free_gb:.2f} GB free")
            else:
                logger.info(f"    ✅ Disk space OK: {free_gb:.2f} GB free")
        except Exception as e:
            logger.warning(f"    ⚠️  Could not check disk space: {e}")

        # Check 5: Database permissions
        logger.info("  ✓ Checking database permissions...")
        try:
            session = self.Session()
            # Try to create a test table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS _migration_test (id SERIAL PRIMARY KEY)
            """))
            session.execute(text("DROP TABLE IF EXISTS _migration_test"))
            session.commit()
            session.close()
            logger.info("    ✅ Database permissions OK (can create/drop tables)")
        except Exception as e:
            logger.error(f"    ❌ Insufficient database permissions: {e}")
            all_passed = False

        # Check 6: Existing data in database
        logger.info("  ✓ Checking for existing posts in database...")
        try:
            session = self.Session()
            result = session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'posts'
            """))
            table_exists = result.scalar() > 0

            if table_exists:
                result = session.execute(text("SELECT COUNT(*) FROM posts"))
                existing_count = result.scalar()
                if existing_count > 0:
                    logger.warning(f"    ⚠️  Database already has {existing_count} posts")
                    logger.warning(f"       Duplicates will be skipped, existing posts won't be overwritten")
                else:
                    logger.info("    ✅ Posts table exists but is empty")
            else:
                logger.info("    ℹ️  Posts table doesn't exist (will be created)")
            session.close()
        except Exception as e:
            logger.warning(f"    ⚠️  Could not check existing posts: {e}")

        # Summary
        logger.info("\n" + "="*60)
        if all_passed:
            logger.info("✅ ALL PRE-FLIGHT CHECKS PASSED")
        else:
            logger.error("❌ SOME PRE-FLIGHT CHECKS FAILED")
            logger.error("   Please fix the issues above before proceeding")
        logger.info("="*60 + "\n")

        return all_passed

    def apply_schema(self, schema_file: str = 'database/schema_posts.sql'):
        """Apply SQL schema to database"""
        logger.info(f"📋 Applying schema from {schema_file}...")

        try:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            with self.engine.connect() as conn:
                # Execute each statement separately
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for stmt in statements:
                    if stmt:
                        try:
                            conn.execute(text(stmt))
                            conn.commit()
                        except Exception as e:
                            # Some statements might fail if objects already exist, that's OK
                            if 'already exists' not in str(e).lower():
                                logger.warning(f"Statement warning: {str(e)[:100]}")

            logger.info("✅ Schema applied successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error applying schema: {e}")
            return False

    def find_json_files(self, search_paths: List[str] = None) -> List[Path]:
        """Find all *_posts_detailed.json files"""
        if search_paths is None:
            search_paths = ['data/processed', 'data/backups']

        json_files = []
        for search_path in search_paths:
            path = Path(search_path)
            if path.exists():
                # Find all *_posts_detailed.json files recursively
                files = list(path.rglob('*_posts_detailed.json'))
                json_files.extend(files)
                logger.info(f"📁 Found {len(files)} JSON files in {search_path}")

        logger.info(f"📊 Total JSON files found: {len(json_files)}")
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

    def migrate_post(self, post_data: Dict, session) -> bool:
        """
        Migrate a single post to PostgreSQL

        Returns:
            True if inserted, False if skipped (already exists)
        """
        post_id = post_data.get('post_id')
        if not post_id:
            logger.warning("⚠️ Post without post_id, skipping")
            return False

        try:
            # Check if post already exists
            result = session.execute(
                text("SELECT 1 FROM posts WHERE post_id = :post_id"),
                {"post_id": post_id}
            )
            if result.fetchone():
                logger.debug(f"⏭️ Post {post_id} already exists, skipping")
                return False

            # Extract downloaded_media paths
            downloaded_media = post_data.get('downloaded_media', {})
            video_local_paths = downloaded_media.get('videos_relative', [])
            audio_local_paths = downloaded_media.get('audios_relative', [])

            # Prepare post metadata
            post_metadata = post_data.get('post_metadata', {})

            # Insert post
            insert_sql = text("""
                INSERT INTO posts (
                    post_id,
                    creator_id,
                    post_url,
                    title,
                    full_content,
                    content_blocks,
                    published_at,
                    created_at,
                    updated_at,
                    scraped_at,
                    creator_name,
                    creator_avatar,
                    like_count,
                    comment_count,
                    images,
                    videos,
                    audios,
                    attachments,
                    image_local_paths,
                    video_local_paths,
                    audio_local_paths,
                    video_downloads,
                    video_streams,
                    video_subtitles,
                    patreon_tags,
                    status
                ) VALUES (
                    :post_id,
                    :creator_id,
                    :post_url,
                    :title,
                    :full_content,
                    CAST(:content_blocks AS jsonb),
                    :published_at,
                    :created_at,
                    :updated_at,
                    :scraped_at,
                    :creator_name,
                    :creator_avatar,
                    :like_count,
                    :comment_count,
                    :images,
                    :videos,
                    :audios,
                    :attachments,
                    :image_local_paths,
                    :video_local_paths,
                    :audio_local_paths,
                    :video_downloads,
                    CAST(:video_streams AS jsonb),
                    CAST(:video_subtitles AS jsonb),
                    :patreon_tags,
                    CAST(:status AS jsonb)
                )
            """)

            session.execute(insert_sql, {
                'post_id': post_id,
                'creator_id': post_data.get('creator_id', ''),
                'post_url': post_data.get('post_url', ''),
                'title': post_data.get('title'),
                'full_content': post_data.get('full_content'),
                'content_blocks': json.dumps(post_data.get('content_blocks', [])),
                'published_at': self.parse_timestamp(post_data.get('published_at')),
                'created_at': self.parse_timestamp(post_data.get('created_at')),
                'updated_at': self.parse_timestamp(post_data.get('updated_at')),
                'scraped_at': self.parse_timestamp(post_data.get('scraped_at')),
                'creator_name': post_metadata.get('creator_name'),
                'creator_avatar': post_data.get('creator_avatar'),
                'like_count': post_data.get('like_count', 0),
                'comment_count': post_metadata.get('comments_count', 0),
                'images': post_data.get('images', []),
                'videos': post_data.get('videos', []),
                'audios': post_data.get('audios', []),
                'attachments': post_data.get('attachments', []),
                'image_local_paths': post_data.get('image_local_paths', []),
                'video_local_paths': video_local_paths,
                'audio_local_paths': audio_local_paths,
                'video_downloads': post_data.get('video_downloads', []),
                'video_streams': json.dumps(downloaded_media.get('video_streams', {})),
                'video_subtitles': json.dumps(downloaded_media.get('video_subtitles', {})),
                'patreon_tags': post_data.get('patreon_tags', []),
                'status': json.dumps(post_data.get('status', {}))
            })

            session.commit()
            return True

        except IntegrityError as e:
            session.rollback()
            logger.debug(f"⏭️ Post {post_id} already exists (integrity error)")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error migrating post {post_id}: {e}")
            return False

    def migrate_file(self, json_file: Path) -> Dict[str, int]:
        """
        Migrate all posts from a JSON file

        Returns:
            Dict with stats: {'inserted': N, 'skipped': N, 'errors': N}
        """
        stats = {'inserted': 0, 'skipped': 0, 'errors': 0}

        try:
            logger.info(f"📖 Reading {json_file}")
            with open(json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)

            if not isinstance(posts, list):
                logger.error(f"❌ Invalid JSON format in {json_file} (expected list)")
                stats['errors'] = 1
                return stats

            session = self.Session()

            for i, post_data in enumerate(posts, 1):
                if self.migrate_post(post_data, session):
                    stats['inserted'] += 1
                    if stats['inserted'] % 10 == 0:
                        logger.info(f"  ✓ Migrated {stats['inserted']}/{len(posts)} posts...")
                else:
                    stats['skipped'] += 1

            session.close()

            logger.info(f"✅ Completed {json_file.name}: "
                       f"inserted={stats['inserted']}, skipped={stats['skipped']}")

        except Exception as e:
            logger.error(f"❌ Error processing {json_file}: {e}")
            stats['errors'] = 1

        return stats

    def migrate_all(self, apply_schema: bool = True, skip_checks: bool = False):
        """Migrate all posts from JSON files to PostgreSQL"""
        logger.info("🚀 Starting migration from JSON to PostgreSQL")

        # Run pre-flight checks first
        if not skip_checks:
            if not self.preflight_checks():
                logger.error("❌ Pre-flight checks failed, aborting migration")
                logger.error("   Fix the issues above or use --skip-checks to bypass")
                return

            # Ask for confirmation
            logger.info("⚠️  Ready to migrate. This will:")
            logger.info("   1. Apply database schema (if needed)")
            logger.info("   2. Insert posts from JSON files into PostgreSQL")
            logger.info("   3. Skip duplicates (existing post_ids won't be modified)")
            response = input("\n👉 Proceed with migration? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                logger.info("❌ Migration cancelled by user")
                return

        # Apply schema first
        if apply_schema:
            if not self.apply_schema():
                logger.error("❌ Failed to apply schema, aborting migration")
                return

        # Find all JSON files
        json_files = self.find_json_files()
        if not json_files:
            logger.warning("⚠️ No JSON files found!")
            return

        # Migrate each file
        total_stats = {'inserted': 0, 'skipped': 0, 'errors': 0}

        for i, json_file in enumerate(json_files, 1):
            logger.info(f"\n📦 Processing file {i}/{len(json_files)}: {json_file.name}")
            stats = self.migrate_file(json_file)

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

        # Show some stats from database
        self.show_database_stats()

    def show_database_stats(self):
        """Show statistics from the database"""
        try:
            session = self.Session()

            # Total posts
            result = session.execute(text("SELECT COUNT(*) FROM posts"))
            total_posts = result.scalar()

            # Posts by creator
            result = session.execute(text("""
                SELECT creator_id, COUNT(*) as count
                FROM posts
                GROUP BY creator_id
                ORDER BY count DESC
                LIMIT 5
            """))
            creators = result.fetchall()

            # Posts with media
            result = session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE array_length(images, 1) > 0) as with_images,
                    COUNT(*) FILTER (WHERE array_length(videos, 1) > 0) as with_videos,
                    COUNT(*) FILTER (WHERE array_length(audios, 1) > 0) as with_audios
                FROM posts
            """))
            media_stats = result.fetchone()

            logger.info("\n📊 DATABASE STATISTICS:")
            logger.info(f"   Total posts: {total_posts}")
            logger.info(f"   Posts with images: {media_stats[0]}")
            logger.info(f"   Posts with videos: {media_stats[1]}")
            logger.info(f"   Posts with audios: {media_stats[2]}")
            logger.info(f"\n👥 Top creators:")
            for creator_id, count in creators:
                logger.info(f"   - {creator_id}: {count} posts")

            session.close()

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate Patreon posts from JSON to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full migration with pre-flight checks
  python src/migrate_json_to_postgres.py

  # Skip checks and confirmation (use with caution!)
  python src/migrate_json_to_postgres.py --skip-checks --yes

  # Only apply schema, don't migrate
  python src/migrate_json_to_postgres.py --schema-only

  # Migrate specific file
  python src/migrate_json_to_postgres.py --file data/processed/astrobymax_posts_detailed.json
        """
    )
    parser.add_argument('--no-schema', action='store_true',
                       help='Skip applying schema (if already applied)')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip pre-flight checks (not recommended)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm (skip confirmation prompt)')
    parser.add_argument('--file', type=str,
                       help='Migrate specific JSON file instead of all')
    parser.add_argument('--schema-only', action='store_true',
                       help='Only apply schema, do not migrate data')

    args = parser.parse_args()

    try:
        migrator = PostMigrator()

        # Schema-only mode
        if args.schema_only:
            logger.info("📋 Schema-only mode")
            if migrator.preflight_checks():
                migrator.apply_schema()
            return

        if args.file:
            # Migrate single file
            logger.info(f"📦 Migrating single file: {args.file}")
            if not args.no_schema:
                migrator.apply_schema()
            stats = migrator.migrate_file(Path(args.file))
            logger.info(f"✅ Done: inserted={stats['inserted']}, skipped={stats['skipped']}")
        else:
            # Migrate all files
            # Handle --yes flag by monkey-patching input
            if args.yes:
                import builtins
                builtins.input = lambda _: "yes"

            migrator.migrate_all(
                apply_schema=not args.no_schema,
                skip_checks=args.skip_checks
            )

    except KeyboardInterrupt:
        logger.info("\n⚠️ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
