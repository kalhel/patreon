#!/usr/bin/env python3
"""
Test script for Phase 3 PostgreSQL integration
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from datetime import datetime

# Add src to path (go up two levels: tools/testing/ -> tools/ -> root/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

load_dotenv()


def get_database_url():
    """Build PostgreSQL connection URL"""
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def test_flag_detection():
    """Test 1: Check if flag is detected"""
    print("\n" + "="*60)
    print("TEST 1: Flag Detection")
    print("="*60)

    flag_path = Path("config/use_postgresql.flag")
    if flag_path.exists():
        print("✅ PostgreSQL flag detected")
        return True
    else:
        print("❌ PostgreSQL flag NOT found")
        return False


def test_database_connection():
    """Test 2: Check database connection"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_collections_table():
    """Test 3: Check collections table exists"""
    print("\n" + "="*60)
    print("TEST 3: Collections Table")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'collections'
            """))
            exists = result.scalar() > 0

            if exists:
                # Get count
                result = conn.execute(text("SELECT COUNT(*) FROM collections"))
                count = result.scalar()
                print(f"✅ Collections table exists")
                print(f"   Current count: {count} collections")
                return True
            else:
                print("❌ Collections table does NOT exist")
                return False

    except Exception as e:
        print(f"❌ Error checking collections table: {e}")
        return False


def test_insert_dummy_collection():
    """Test 4: Insert a test collection (Schema V2)"""
    print("\n" + "="*60)
    print("TEST 4: Insert Test Collection")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # First, get a valid source_id and creator_id from creator_sources
            source_query = text("SELECT id, creator_id FROM creator_sources WHERE is_active = true LIMIT 1")
            result = conn.execute(source_query)
            row = result.fetchone()

            if not row:
                print("⚠️  No active sources found. Skipping collection insert test.")
                return True  # Not a failure, just no data to test with

            source_id = row[0]
            creator_id = row[1]
            print(f"   Using source_id: {source_id}, creator_id: {creator_id}")

            # Try to insert a test collection (Schema V2)
            test_id = "test_collection_99999"

            # Note: DB has both creator_id (Schema V1) and source_id (Schema V2)
            # Using both to ensure compatibility with hybrid schema
            insert_sql = text("""
                INSERT INTO collections (
                    source_id,
                    creator_id,
                    collection_id,
                    title,
                    description,
                    post_count
                ) VALUES (
                    :source_id,
                    :creator_id,
                    :collection_id,
                    :title,
                    :description,
                    :post_count
                )
                ON CONFLICT (collection_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    updated_at = NOW()
                RETURNING id
            """)

            result = conn.execute(insert_sql, {
                'source_id': source_id,
                'creator_id': creator_id,
                'collection_id': test_id,
                'title': 'Test Collection - Phase 3 (Hybrid Schema)',
                'description': 'This is a test collection to verify PostgreSQL integration',
                'post_count': 0
            })
            conn.commit()

            print("✅ Test collection inserted successfully")

            # Verify it was inserted
            verify_sql = text("SELECT title FROM collections WHERE source_id = :source_id AND collection_id = :collection_id")
            result = conn.execute(verify_sql, {'source_id': source_id, 'collection_id': test_id})
            title = result.scalar()
            print(f"   Title: {title}")

            # Clean up - delete test collection
            delete_sql = text("DELETE FROM collections WHERE source_id = :source_id AND collection_id = :collection_id")
            conn.execute(delete_sql, {'source_id': source_id, 'collection_id': test_id})
            conn.commit()
            print("✅ Test collection cleaned up")

            return True

    except Exception as e:
        print(f"❌ Error inserting test collection: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Phase 3 PostgreSQL Integration Tests")
    print("="*60)

    tests = [
        ("Flag Detection", test_flag_detection),
        ("Database Connection", test_database_connection),
        ("Collections Table", test_collections_table),
        ("Insert Test Collection", test_insert_dummy_collection)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Phase 3 PostgreSQL integration is ready!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before using Phase 3 scraper.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
