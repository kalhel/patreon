#!/usr/bin/env python3
"""
Migrate Firebase tracking data to PostgreSQL
This script migrates post tracking status from Firebase to the new scraping_status table
"""

import sys
import os
import json
import requests
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psycopg2
    from psycopg2.extras import execute_values, Json
except ImportError:
    print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Using environment variables.")


def get_firebase_data():
    """Fetch all data from Firebase"""
    firebase_url = os.getenv('FIREBASE_DATABASE_URL')
    firebase_secret = os.getenv('FIREBASE_DATABASE_SECRET')

    if not firebase_url or not firebase_secret:
        print("❌ Firebase credentials not found in environment")
        print("Set FIREBASE_DATABASE_URL and FIREBASE_DATABASE_SECRET in .env")
        return None

    print(f"📡 Fetching data from Firebase: {firebase_url}")

    try:
        # Fetch all posts data
        url = f"{firebase_url}/posts.json?auth={firebase_secret}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not data:
            print("⚠️  No data found in Firebase")
            return {}

        print(f"✅ Fetched {len(data)} posts from Firebase")
        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch from Firebase: {e}")
        return None


def get_db_connection():
    """Create PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'patreon'),
            user=os.getenv('DB_USER', 'patreon_user'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        return None


def get_creator_id(cursor, creator_name):
    """Get creator ID from database, create if doesn't exist"""
    cursor.execute(
        "SELECT id FROM creators WHERE creator_id = %s",
        (creator_name,)
    )
    result = cursor.fetchone()

    if result:
        return result[0]

    # Create creator if doesn't exist
    cursor.execute("""
        INSERT INTO creators (creator_id, name, active)
        VALUES (%s, %s, true)
        RETURNING id
    """, (creator_name, creator_name.replace('_', ' ').title()))

    return cursor.fetchone()[0]


def migrate_firebase_to_postgres(firebase_data, conn):
    """Migrate Firebase data to PostgreSQL scraping_status table"""

    if not firebase_data:
        print("⚠️  No data to migrate")
        return 0

    cursor = conn.cursor()
    migrated_count = 0
    error_count = 0

    print(f"\n📊 Migrating {len(firebase_data)} posts...")

    for post_id, post_data in firebase_data.items():
        try:
            # Extract Firebase data
            creator_name = post_data.get('creator', 'unknown')
            post_url = post_data.get('url') or f"https://www.patreon.com/posts/{post_id}"

            # Extract status from Firebase structure
            status_obj = post_data.get('status', {})
            if isinstance(status_obj, dict):
                # Firebase has complex status object, extract simple state
                if status_obj.get('details_extracted'):
                    phase2_status = 'completed'
                elif status_obj.get('errors'):
                    phase2_status = 'failed'
                else:
                    phase2_status = 'pending'
            else:
                # Simple string status
                phase2_status = status_obj if status_obj in ['pending', 'completed', 'failed'] else 'pending'

            # Get or create creator
            creator_id = get_creator_id(cursor, creator_name)

            # Map Firebase status to phase statuses
            phase1_status = 'completed'  # If it's in Firebase, phase1 was completed

            # Insert into scraping_status
            cursor.execute("""
                INSERT INTO scraping_status (
                    post_id, creator_id, post_url,
                    phase1_status, phase1_completed_at,
                    phase2_status,
                    firebase_migrated, firebase_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (post_id) DO UPDATE SET
                    phase2_status = EXCLUDED.phase2_status,
                    firebase_data = EXCLUDED.firebase_data,
                    firebase_migrated = true,
                    updated_at = NOW()
            """, (
                post_id,
                creator_id,
                post_url,
                phase1_status,
                datetime.now(),
                phase2_status,
                True,
                Json(post_data)
            ))

            migrated_count += 1

            if migrated_count % 100 == 0:
                print(f"   ... migrated {migrated_count} posts")

        except Exception as e:
            print(f"⚠️  Error migrating post {post_id}: {e}")
            error_count += 1
            continue

    # Commit transaction
    conn.commit()
    cursor.close()

    print(f"\n✅ Migration complete:")
    print(f"   - Migrated: {migrated_count}")
    print(f"   - Errors: {error_count}")

    return migrated_count


def verify_migration(conn):
    """Verify migration was successful"""
    cursor = conn.cursor()

    # Count migrated posts
    cursor.execute("SELECT COUNT(*) FROM scraping_status WHERE firebase_migrated = true")
    migrated_count = cursor.fetchone()[0]

    # Count by status
    cursor.execute("""
        SELECT phase2_status, COUNT(*)
        FROM scraping_status
        WHERE firebase_migrated = true
        GROUP BY phase2_status
    """)
    status_counts = cursor.fetchall()

    # Count by creator
    cursor.execute("""
        SELECT c.name, COUNT(*)
        FROM scraping_status ss
        JOIN creators c ON c.id = ss.creator_id
        WHERE ss.firebase_migrated = true
        GROUP BY c.name
    """)
    creator_counts = cursor.fetchall()

    print(f"\n📊 Migration Statistics:")
    print(f"   Total migrated: {migrated_count}")
    print(f"\n   By status:")
    for status, count in status_counts:
        print(f"      - {status}: {count}")
    print(f"\n   By creator:")
    for creator, count in creator_counts:
        print(f"      - {creator}: {count}")

    cursor.close()


def backup_firebase_data(firebase_data):
    """Save a backup of Firebase data"""
    backup_dir = "data/backups"
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/firebase_backup_{timestamp}.json"

    with open(backup_file, 'w') as f:
        json.dump(firebase_data, f, indent=2)

    print(f"💾 Firebase data backed up to: {backup_file}")


def main():
    print("=" * 70)
    print("🔄 Firebase to PostgreSQL Migration")
    print("=" * 70)
    print()

    # Fetch Firebase data
    firebase_data = get_firebase_data()
    if firebase_data is None:
        return 1

    # Backup Firebase data
    if firebase_data:
        backup_firebase_data(firebase_data)

    # Connect to PostgreSQL
    conn = get_db_connection()
    if not conn:
        return 1

    # Check if scraping_status table exists
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'scraping_status'
        );
    """)
    table_exists = cursor.fetchone()[0]
    cursor.close()

    if not table_exists:
        print("❌ Table 'scraping_status' does not exist")
        print("Run database/schema.sql first: psql -U patreon_user -d patreon -f database/schema.sql")
        conn.close()
        return 1

    # Ask for confirmation
    print(f"\n⚠️  About to migrate {len(firebase_data)} posts to PostgreSQL")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        conn.close()
        return 0

    # Migrate
    migrated_count = migrate_firebase_to_postgres(firebase_data, conn)

    # Verify
    if migrated_count > 0:
        verify_migration(conn)

    conn.close()

    print("\n" + "=" * 70)
    print("✅ Migration Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Verify data in PostgreSQL: psql -U patreon_user -d patreon")
    print("  2. Query: SELECT * FROM scraping_status LIMIT 10;")
    print("  3. Update scripts to use PostgreSQL instead of Firebase")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
