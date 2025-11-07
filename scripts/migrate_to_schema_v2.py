#!/usr/bin/env python3
"""
Migration Script: Schema V1 → Schema V2 (Multi-Source Design)

This script migrates data from the old schema (one creator = one platform)
to the new multi-source schema (one creator with multiple sources).

Steps:
1. Backup current database (pg_dump)
2. Extract unique creators from current schema
3. Create new creators table (platform-agnostic)
4. Create creator_sources for each platform
5. Migrate posts to reference sources
6. Migrate scraping_status with source_id
7. Verify data integrity
8. Generate migration report

Run with: python scripts/migrate_to_schema_v2.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text, MetaData, Table, select, func
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor


class SchemaV2Migration:
    """Handles migration from schema v1 to v2"""

    def __init__(self, db_url):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.report = {
            'started_at': datetime.now().isoformat(),
            'steps': [],
            'errors': [],
            'stats': {}
        }

    def log(self, message, step=None):
        """Log migration step"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if step:
            self.report['steps'].append({
                'step': step,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })

    def error(self, message):
        """Log error"""
        print(f"❌ ERROR: {message}")
        self.report['errors'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def check_current_schema(self):
        """Verify we're running on schema v1"""
        self.log("Checking current schema version...", "check_schema")

        with self.engine.connect() as conn:
            # Check if creator_sources exists (would indicate v2)
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'creator_sources'
                )
            """))

            if result.scalar():
                self.error("Schema V2 already exists! Migration already run or database is v2.")
                return False

            # Check if creators table exists (v1)
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'creators'
                )
            """))

            if not result.scalar():
                self.error("No 'creators' table found. Database might be empty.")
                return False

        self.log("✅ Schema V1 detected. Safe to migrate.")
        return True

    def analyze_current_data(self):
        """Analyze current data before migration"""
        self.log("Analyzing current data...", "analyze_data")

        with self.engine.connect() as conn:
            # Count creators
            result = conn.execute(text("SELECT COUNT(*) FROM creators"))
            creator_count = result.scalar()

            # Count posts in scraping_status
            result = conn.execute(text("SELECT COUNT(*) FROM scraping_status"))
            post_count = result.scalar()

            # Get creator details
            result = conn.execute(text("""
                SELECT
                    c.creator_id,
                    c.name,
                    COUNT(ss.id) as post_count
                FROM creators c
                LEFT JOIN scraping_status ss ON ss.creator_id = c.id
                GROUP BY c.id, c.creator_id, c.name
                ORDER BY c.name
            """))
            creators = result.fetchall()

        self.report['stats']['before_migration'] = {
            'total_creators': creator_count,
            'total_posts': post_count,
            'creators': [
                {
                    'name': row[1],
                    'creator_id': row[0],
                    'posts': row[2]
                }
                for row in creators
            ]
        }

        self.log(f"  Creators: {creator_count}")
        self.log(f"  Posts in scraping_status: {post_count}")
        for row in creators:
            self.log(f"    • {row[1]} ({row[0]}): {row[2]} posts")

        return True

    def create_backup(self):
        """Create database backup before migration"""
        self.log("Creating database backup...", "backup")

        backup_dir = Path(__file__).parent.parent / "database" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"schema_v1_backup_{timestamp}.sql"

        # Get connection details from environment variables (more reliable than parsing URL)
        db_host = os.getenv('DB_HOST', '127.0.0.1')
        db_port = os.getenv('DB_PORT', '5432')
        db_user = os.getenv('DB_USER', 'patreon_user')
        db_name = os.getenv('DB_NAME', 'alejandria')
        db_password = os.getenv('DB_PASSWORD')

        # Debug: Show connection details (without password)
        self.log(f"  Host: {db_host}")
        self.log(f"  Port: {db_port}")
        self.log(f"  User: {db_user}")
        self.log(f"  Database: {db_name}")

        if not db_password:
            self.error("DB_PASSWORD not found in environment variables")
            return False

        # Run pg_dump
        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-d', db_name,
            '-f', str(backup_file),
            '--clean',
            '--if-exists'
        ]

        import subprocess
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password

            # Run with stderr capture for better error messages
            result = subprocess.run(
                cmd,
                check=True,
                env=env,
                capture_output=True,
                text=True
            )

            self.log(f"✅ Backup created: {backup_file}")
            self.report['backup_file'] = str(backup_file)
            return True
        except subprocess.CalledProcessError as e:
            self.error(f"Backup failed: {e}")
            if e.stderr:
                self.error(f"pg_dump stderr: {e.stderr}")
            if e.stdout:
                self.error(f"pg_dump stdout: {e.stdout}")
            return False

    def create_new_tables(self):
        """Create new schema v2 tables"""
        self.log("Creating schema v2 tables...", "create_tables")

        schema_v2_file = Path(__file__).parent.parent / "database" / "schema_v2.sql"

        if not schema_v2_file.exists():
            self.error(f"Schema V2 file not found: {schema_v2_file}")
            return False

        with open(schema_v2_file, 'r') as f:
            schema_sql = f.read()

        # Drop everything - nuclear option but guaranteed to work
        # NOTE: This is safe because we have a backup
        self.log("  Dropping entire public schema...")
        with self.engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO patreon_user"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.commit()
        self.log("  ✅ Schema dropped and recreated")

        # Execute schema_v2.sql
        with self.engine.connect() as conn:
            conn.execute(text(schema_sql))
            conn.commit()

        self.log("✅ Schema V2 tables created")
        return True

    def migrate_creators(self, old_data):
        """Migrate creators to new schema"""
        self.log("Migrating creators...", "migrate_creators")

        # old_data is from backup - extract unique creator names
        creator_map = {}  # old_creator_id -> new_creator_id

        with self.engine.connect() as conn:
            # For each old creator, create a new platform-agnostic creator
            for old_creator in old_data['creators']:
                name = old_creator['name']
                old_id = old_creator['id']

                # Insert into new creators table (no platform info)
                result = conn.execute(text("""
                    INSERT INTO creators (name, display_name, active)
                    VALUES (:name, :name, true)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """), {'name': name})

                new_creator_id = result.scalar()
                creator_map[old_id] = new_creator_id

                self.log(f"  • Migrated creator: {name} (old_id={old_id} → new_id={new_creator_id})")

            conn.commit()

        self.report['creator_map'] = creator_map
        self.log(f"✅ Migrated {len(creator_map)} creators")
        return creator_map

    def migrate_creator_sources(self, old_data, creator_map):
        """Create creator_sources for each old creator"""
        self.log("Creating creator sources...", "migrate_sources")

        source_map = {}  # old_creator_id -> new_source_id

        with self.engine.connect() as conn:
            for old_creator in old_data['creators']:
                old_id = old_creator['id']
                new_creator_id = creator_map[old_id]

                # Get platform info from old creator
                creator_id_str = old_creator.get('creator_id', old_creator['name'].lower())
                patreon_url = old_creator.get('patreon_url', f"https://www.patreon.com/{creator_id_str}")

                # Create a 'patreon' source for this creator
                result = conn.execute(text("""
                    INSERT INTO creator_sources (
                        creator_id, platform, platform_id, platform_url,
                        platform_username, is_active, scraper_enabled
                    ) VALUES (
                        :creator_id, 'patreon', :platform_id, :platform_url,
                        :username, true, true
                    )
                    RETURNING id
                """), {
                    'creator_id': new_creator_id,
                    'platform_id': creator_id_str,
                    'platform_url': patreon_url,
                    'username': creator_id_str
                })

                new_source_id = result.scalar()
                source_map[old_id] = new_source_id

                self.log(f"  • Created Patreon source for {old_creator['name']} (source_id={new_source_id})")

            conn.commit()

        self.report['source_map'] = source_map
        self.log(f"✅ Created {len(source_map)} sources")
        return source_map

    def migrate_scraping_status(self, old_data, source_map):
        """Migrate scraping_status to reference sources"""
        self.log("Migrating scraping_status...", "migrate_scraping_status")

        migrated_count = 0

        with self.engine.connect() as conn:
            for old_status in old_data['scraping_status']:
                old_creator_id = old_status['creator_id']
                source_id = source_map.get(old_creator_id)

                if not source_id:
                    self.error(f"No source found for old_creator_id={old_creator_id}")
                    continue

                # Insert into new scraping_status
                conn.execute(text("""
                    INSERT INTO scraping_status (
                        post_id, source_id, post_url,
                        phase1_status, phase1_completed_at,
                        phase2_status, phase2_completed_at, phase2_attempts,
                        has_images, has_videos, has_audio,
                        firebase_migrated, firebase_data
                    ) VALUES (
                        :post_id, :source_id, :post_url,
                        :phase1_status, :phase1_completed_at,
                        :phase2_status, :phase2_completed_at, :phase2_attempts,
                        :has_images, :has_videos, :has_audio,
                        :firebase_migrated, :firebase_data::jsonb
                    )
                    ON CONFLICT (source_id, post_id) DO NOTHING
                """), {
                    'post_id': old_status['post_id'],
                    'source_id': source_id,
                    'post_url': old_status['post_url'],
                    'phase1_status': old_status.get('phase1_status', 'completed'),
                    'phase1_completed_at': old_status.get('phase1_completed_at'),
                    'phase2_status': old_status.get('phase2_status', 'pending'),
                    'phase2_completed_at': old_status.get('phase2_completed_at'),
                    'phase2_attempts': old_status.get('phase2_attempts', 0),
                    'has_images': old_status.get('has_images', False),
                    'has_videos': old_status.get('has_videos', False),
                    'has_audio': old_status.get('has_audio', False),
                    'firebase_migrated': old_status.get('firebase_migrated', False),
                    'firebase_data': json.dumps(old_status.get('firebase_data')) if old_status.get('firebase_data') else None
                })

                migrated_count += 1

                if migrated_count % 100 == 0:
                    self.log(f"  Migrated {migrated_count} posts...")

            conn.commit()

        self.log(f"✅ Migrated {migrated_count} scraping_status records")
        self.report['stats']['migrated_posts'] = migrated_count
        return migrated_count

    def verify_migration(self):
        """Verify data integrity after migration"""
        self.log("Verifying migration...", "verify")

        with self.engine.connect() as conn:
            # Count new creators
            result = conn.execute(text("SELECT COUNT(*) FROM creators"))
            new_creator_count = result.scalar()

            # Count new sources
            result = conn.execute(text("SELECT COUNT(*) FROM creator_sources"))
            new_source_count = result.scalar()

            # Count new scraping_status
            result = conn.execute(text("SELECT COUNT(*) FROM scraping_status"))
            new_post_count = result.scalar()

            # Get stats per creator
            result = conn.execute(text("""
                SELECT
                    c.name,
                    COUNT(DISTINCT cs.id) as source_count,
                    COUNT(DISTINCT ss.id) as post_count
                FROM creators c
                LEFT JOIN creator_sources cs ON cs.creator_id = c.id
                LEFT JOIN scraping_status ss ON ss.source_id = cs.id
                GROUP BY c.id, c.name
                ORDER BY c.name
            """))
            new_stats = result.fetchall()

        self.report['stats']['after_migration'] = {
            'total_creators': new_creator_count,
            'total_sources': new_source_count,
            'total_posts': new_post_count,
            'creators': [
                {
                    'name': row[0],
                    'sources': row[1],
                    'posts': row[2]
                }
                for row in new_stats
            ]
        }

        self.log(f"  Creators: {new_creator_count}")
        self.log(f"  Sources: {new_source_count}")
        self.log(f"  Posts: {new_post_count}")

        for row in new_stats:
            self.log(f"    • {row[0]}: {row[1]} source(s), {row[2]} post(s)")

        # Verify counts match
        old_posts = self.report['stats']['before_migration']['total_posts']
        if new_post_count == old_posts:
            self.log("✅ Post count matches!")
        else:
            self.error(f"Post count mismatch: old={old_posts}, new={new_post_count}")

        return True

    def save_report(self):
        """Save migration report"""
        report_dir = Path(__file__).parent.parent / "database" / "migration_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f"migration_v1_to_v2_{timestamp}.json"

        self.report['completed_at'] = datetime.now().isoformat()

        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2)

        self.log(f"✅ Report saved: {report_file}")
        return report_file

    def run(self):
        """Run full migration"""
        print("=" * 60)
        print("  Schema V1 → V2 Migration")
        print("  Multi-Source Design Implementation")
        print("=" * 60)
        print()

        # Step 1: Check schema
        if not self.check_current_schema():
            return False

        # Step 2: Analyze data
        if not self.analyze_current_data():
            return False

        # Step 3: Backup old data in memory (since we'll drop tables)
        self.log("Loading old data into memory...", "load_old_data")
        old_data = {'creators': [], 'scraping_status': []}

        with self.engine.connect() as conn:
            # Load creators
            result = conn.execute(text("""
                SELECT id, creator_id, name, avatar_url, patreon_url, active, metadata
                FROM creators
            """))
            old_data['creators'] = [
                {
                    'id': row[0],
                    'creator_id': row[1],
                    'name': row[2],
                    'avatar_url': row[3],
                    'patreon_url': row[4],
                    'active': row[5],
                    'metadata': row[6]
                }
                for row in result.fetchall()
            ]

            # Load scraping_status
            result = conn.execute(text("""
                SELECT id, post_id, creator_id, post_url, phase1_status, phase1_completed_at,
                       phase2_status, phase2_completed_at, phase2_attempts,
                       has_images, has_videos, has_audio,
                       firebase_migrated, firebase_data
                FROM scraping_status
            """))
            old_data['scraping_status'] = [
                {
                    'id': row[0],
                    'post_id': row[1],
                    'creator_id': row[2],
                    'post_url': row[3],
                    'phase1_status': row[4],
                    'phase1_completed_at': row[5],
                    'phase2_status': row[6],
                    'phase2_completed_at': row[7],
                    'phase2_attempts': row[8],
                    'has_images': row[9],
                    'has_videos': row[10],
                    'has_audio': row[11],
                    'firebase_migrated': row[12],
                    'firebase_data': row[13]
                }
                for row in result.fetchall()
            ]

        self.log(f"✅ Loaded {len(old_data['creators'])} creators and {len(old_data['scraping_status'])} posts")

        # Step 4: Create backup (SQL dump)
        if not self.create_backup():
            print("\n⚠️  Backup failed! Aborting migration for safety.")
            return False

        # Step 5: Create new schema
        print("\n⚠️  WARNING: About to drop old tables and create schema v2")
        print("   Backup saved. Data is safe.")
        response = input("   Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration aborted by user.")
            return False

        if not self.create_new_tables():
            return False

        # Step 6: Migrate creators
        creator_map = self.migrate_creators(old_data)
        if not creator_map:
            return False

        # Step 7: Migrate sources
        source_map = self.migrate_creator_sources(old_data, creator_map)
        if not source_map:
            return False

        # Step 8: Migrate scraping_status
        if not self.migrate_scraping_status(old_data, source_map):
            return False

        # Step 9: Verify
        if not self.verify_migration():
            return False

        # Step 10: Save report
        report_file = self.save_report()

        print()
        print("=" * 60)
        print("  ✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"  Report: {report_file}")
        print(f"  Backup: {self.report.get('backup_file', 'N/A')}")
        print()
        print("  Next steps:")
        print("  1. Verify web viewer still works")
        print("  2. Test PostgresTracker with new schema")
        print("  3. Update scripts to use multi-source queries")
        print("=" * 60)

        return True


def main():
    """Main entry point"""
    # Load database URL from .env
    from dotenv import load_dotenv
    load_dotenv()

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in .env")
        return 1

    migration = SchemaV2Migration(db_url)
    success = migration.run()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
