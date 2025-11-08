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

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

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
    """Test 4: Insert a test collection"""
    print("\n" + "="*60)
    print("TEST 4: Insert Test Collection")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Try to insert a test collection
            test_id = "test_collection_99999"

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
                ON CONFLICT (collection_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    updated_at = NOW()
                RETURNING id
            """)

            result = conn.execute(insert_sql, {
                'collection_id': test_id,
                'creator_id': 'test_creator',
                'title': 'Test Collection - Phase 3 Dual Mode',
                'description': 'This is a test collection to verify PostgreSQL integration',
                'collection_url': 'https://www.patreon.com/collection/99999',
                'post_count': 0,
                'scraped_at': datetime.now().isoformat()
            })
            conn.commit()

            print("✅ Test collection inserted successfully")

            # Verify it was inserted
            verify_sql = text("SELECT title FROM collections WHERE collection_id = :id")
            result = conn.execute(verify_sql, {'id': test_id})
            title = result.scalar()
            print(f"   Title: {title}")

            # Clean up - delete test collection
            delete_sql = text("DELETE FROM collections WHERE collection_id = :id")
            conn.execute(delete_sql, {'id': test_id})
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
