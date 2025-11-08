#!/usr/bin/env python3
"""
Diagnostic Script - Check Phase 2 and Phase 3 data availability
Compares PostgreSQL data vs JSON files to determine what's available

This script will be moved to archive/ after diagnosis is complete.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Paths
PROCESSED_DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
CONFIG_DIR = Path(__file__).parent.parent / "config"

def get_database_url():
    """Build PostgreSQL connection URL from environment variables"""
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in environment variables")

    # URL encode password to handle special characters
    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def load_creators():
    """Load creators from config file"""
    creators_file = CONFIG_DIR / "creators.json"
    if not creators_file.exists():
        print(f"❌ Creators file not found: {creators_file}")
        return []

    with open(creators_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('creators', [])


def check_json_data(creator_id):
    """Check JSON files for a creator"""
    results = {
        'phase2_json': {'exists': False, 'count': 0, 'last_updated': None},
        'phase3_json': {'exists': False, 'count': 0, 'last_updated': None}
    }

    # Phase 2: Posts detailed
    posts_file = PROCESSED_DATA_DIR / f"{creator_id}_posts_detailed.json"
    if posts_file.exists():
        try:
            with open(posts_file, 'r', encoding='utf-8') as f:
                posts_data = json.load(f)
                results['phase2_json']['exists'] = True
                results['phase2_json']['count'] = len(posts_data)
                results['phase2_json']['last_updated'] = datetime.fromtimestamp(
                    posts_file.stat().st_mtime
                ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"  ⚠️  Error reading {posts_file.name}: {e}")

    # Phase 3: Collections
    collections_file = PROCESSED_DATA_DIR / f"{creator_id}_collections.json"
    if collections_file.exists():
        try:
            with open(collections_file, 'r', encoding='utf-8') as f:
                collections_data = json.load(f)
                results['phase3_json']['exists'] = True
                results['phase3_json']['count'] = len(collections_data.get('collections', []))
                results['phase3_json']['last_updated'] = datetime.fromtimestamp(
                    collections_file.stat().st_mtime
                ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"  ⚠️  Error reading {collections_file.name}: {e}")

    return results


def check_postgresql_data(engine):
    """Check PostgreSQL tables for Phase 2 and Phase 3 data"""
    results = {}

    with engine.connect() as conn:
        # Get all creators from creator_sources
        creators_query = text("""
            SELECT
                c.name as creator_name,
                cs.platform_id as creator_id,
                cs.platform
            FROM creators c
            JOIN creator_sources cs ON c.id = cs.creator_id
            WHERE cs.platform = 'patreon'
            ORDER BY c.name
        """)

        creators_result = conn.execute(creators_query)
        db_creators = creators_result.fetchall()

        for row in db_creators:
            creator_name = row[0]
            creator_id = row[1]

            # Phase 1: scraping_status (URL collection)
            phase1_query = text("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN phase1_status = 'completed' THEN 1 ELSE 0 END) as collected
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                WHERE cs.platform_id = :creator_id
            """)
            phase1_result = conn.execute(phase1_query, {'creator_id': creator_id}).fetchone()

            # Phase 2: posts table (detail extraction)
            # Note: posts table uses schema v1 (creator_id VARCHAR, not source_id)
            phase2_query = text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN full_content IS NOT NULL AND full_content != '' THEN 1 END) as with_content,
                    COUNT(CASE WHEN content_blocks IS NOT NULL THEN 1 END) as with_blocks,
                    MAX(updated_at) as last_updated
                FROM posts p
                WHERE p.creator_id = :creator_id
                  AND p.deleted_at IS NULL
            """)
            phase2_result = conn.execute(phase2_query, {'creator_id': creator_id}).fetchone()

            # Phase 3: collections table
            # Note: collections table uses schema v1 (creator_id VARCHAR, not source_id)
            phase3_query = text("""
                SELECT
                    COUNT(DISTINCT col.id) as total_collections,
                    COUNT(pc.post_id) as total_post_collection_links,
                    MAX(col.updated_at) as last_updated
                FROM collections col
                LEFT JOIN post_collections pc ON pc.collection_id = col.collection_id
                WHERE col.creator_id = :creator_id
                  AND col.deleted_at IS NULL
            """)
            phase3_result = conn.execute(phase3_query, {'creator_id': creator_id}).fetchone()

            results[creator_id] = {
                'creator_name': creator_name,
                'phase1_db': {
                    'total': phase1_result[0] if phase1_result else 0,
                    'collected': phase1_result[1] if phase1_result else 0
                },
                'phase2_db': {
                    'total': phase2_result[0] if phase2_result else 0,
                    'with_content': phase2_result[1] if phase2_result else 0,
                    'with_blocks': phase2_result[2] if phase2_result else 0,
                    'last_updated': phase2_result[3].strftime('%Y-%m-%d %H:%M:%S') if phase2_result and phase2_result[3] else None
                },
                'phase3_db': {
                    'total_collections': phase3_result[0] if phase3_result else 0,
                    'total_links': phase3_result[1] if phase3_result else 0,
                    'last_updated': phase3_result[2].strftime('%Y-%m-%d %H:%M:%S') if phase3_result and phase3_result[2] else None
                }
            }

    return results


def print_comparison(creator_id, creator_name, pg_data, json_data):
    """Print comparison for a creator"""
    print(f"\n{'='*80}")
    print(f"📊 CREATOR: {creator_name} ({creator_id})")
    print(f"{'='*80}")

    # Phase 1 (only in PostgreSQL)
    print(f"\n🔵 PHASE 1 - URL Collection (PostgreSQL only)")
    print(f"  Total posts in scraping_status: {pg_data['phase1_db']['total']}")
    print(f"  URLs collected: {pg_data['phase1_db']['collected']}")

    # Phase 2 comparison
    print(f"\n🔵 PHASE 2 - Detail Extraction")
    print(f"  PostgreSQL (posts table):")
    print(f"    - Total posts: {pg_data['phase2_db']['total']}")
    print(f"    - Posts with content: {pg_data['phase2_db']['with_content']}")
    print(f"    - Posts with content_blocks: {pg_data['phase2_db']['with_blocks']}")
    print(f"    - Last updated: {pg_data['phase2_db']['last_updated'] or 'Never'}")

    print(f"  JSON file (_posts_detailed.json):")
    if json_data['phase2_json']['exists']:
        print(f"    - ✅ Exists")
        print(f"    - Posts count: {json_data['phase2_json']['count']}")
        print(f"    - Last modified: {json_data['phase2_json']['last_updated']}")
    else:
        print(f"    - ❌ Does not exist")

    # Phase 2 verdict
    if pg_data['phase2_db']['with_content'] > 0:
        print(f"  ✅ PostgreSQL has Phase 2 data ({pg_data['phase2_db']['with_content']} posts with content)")
    else:
        print(f"  ❌ PostgreSQL has NO Phase 2 content data")

    # Phase 3 comparison
    print(f"\n🔵 PHASE 3 - Collections")
    print(f"  PostgreSQL (collections table):")
    print(f"    - Total collections: {pg_data['phase3_db']['total_collections']}")
    print(f"    - Post-collection links: {pg_data['phase3_db']['total_links']}")
    print(f"    - Last updated: {pg_data['phase3_db']['last_updated'] or 'Never'}")

    print(f"  JSON file (_collections.json):")
    if json_data['phase3_json']['exists']:
        print(f"    - ✅ Exists")
        print(f"    - Collections count: {json_data['phase3_json']['count']}")
        print(f"    - Last modified: {json_data['phase3_json']['last_updated']}")
    else:
        print(f"    - ❌ Does not exist")

    # Phase 3 verdict
    if pg_data['phase3_db']['total_collections'] > 0:
        print(f"  ✅ PostgreSQL has Phase 3 data ({pg_data['phase3_db']['total_collections']} collections)")
    else:
        print(f"  ❌ PostgreSQL has NO Phase 3 data")


def main():
    """Main diagnostic function"""
    print("="*80)
    print("🔍 DIAGNOSTIC: Phase 2 & Phase 3 Data Availability")
    print("="*80)
    print("\nThis script checks if Phase 2 and Phase 3 data exists in:")
    print("  - PostgreSQL database (posts, collections tables)")
    print("  - JSON files (data/processed/)")

    # Load creators
    print("\n📋 Loading creators from config...")
    creators = load_creators()
    if not creators:
        print("❌ No creators found!")
        return 1
    print(f"✅ Found {len(creators)} creators")

    # Connect to PostgreSQL
    print("\n🔌 Connecting to PostgreSQL...")
    try:
        db_url = get_database_url()
        engine = create_engine(db_url, pool_pre_ping=True)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ PostgreSQL connected")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        return 1

    # Check PostgreSQL data
    print("\n📊 Querying PostgreSQL tables...")
    pg_results = check_postgresql_data(engine)
    print(f"✅ Found data for {len(pg_results)} creators in PostgreSQL")

    # Check each creator
    for creator in creators:
        creator_id = creator['creator_id']
        creator_name = creator['name']

        # Get JSON data
        json_data = check_json_data(creator_id)

        # Get PostgreSQL data
        pg_data = pg_results.get(creator_id, {
            'creator_name': creator_name,
            'phase1_db': {'total': 0, 'collected': 0},
            'phase2_db': {'total': 0, 'with_content': 0, 'with_blocks': 0, 'last_updated': None},
            'phase3_db': {'total_collections': 0, 'total_links': 0, 'last_updated': None}
        })

        # Print comparison
        print_comparison(creator_id, creator_name, pg_data, json_data)

    # Summary
    print("\n" + "="*80)
    print("📝 SUMMARY & RECOMMENDATIONS")
    print("="*80)

    total_phase2_in_pg = sum(1 for data in pg_results.values() if data['phase2_db']['with_content'] > 0)
    total_phase3_in_pg = sum(1 for data in pg_results.values() if data['phase3_db']['total_collections'] > 0)

    print(f"\nPhase 2 (Detail Extraction):")
    print(f"  - Creators with data in PostgreSQL: {total_phase2_in_pg}/{len(creators)}")
    if total_phase2_in_pg == len(creators):
        print(f"  ✅ All creators have Phase 2 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Update settings page to read from PostgreSQL")
    elif total_phase2_in_pg > 0:
        print(f"  ⚠️  Some creators have Phase 2 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Re-run Phase 2 for missing creators, then update settings")
    else:
        print(f"  ❌ NO Phase 2 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Keep reading from JSON OR re-run Phase 2 to populate PostgreSQL")

    print(f"\nPhase 3 (Collections):")
    print(f"  - Creators with data in PostgreSQL: {total_phase3_in_pg}/{len(creators)}")
    if total_phase3_in_pg == len(creators):
        print(f"  ✅ All creators have Phase 3 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Update settings page to read from PostgreSQL")
    elif total_phase3_in_pg > 0:
        print(f"  ⚠️  Some creators have Phase 3 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Re-run Phase 3 for missing creators, then update settings")
    else:
        print(f"  ❌ NO Phase 3 data in PostgreSQL")
        print(f"  👉 RECOMMENDATION: Keep reading from JSON OR run Phase 3 migration script")

    print("\n" + "="*80)
    print("✅ Diagnostic complete!")
    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
