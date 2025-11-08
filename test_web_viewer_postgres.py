#!/usr/bin/env python3
"""
Test script for Web Viewer PostgreSQL integration
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

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
        print("   To enable: touch config/use_postgresql.flag")
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


def test_load_posts():
    """Test 3: Test loading posts from PostgreSQL"""
    print("\n" + "="*60)
    print("TEST 3: Load Posts from PostgreSQL")
    print("="*60)

    try:
        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Count total posts
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM posts
                WHERE deleted_at IS NULL
            """))
            total_posts = result.scalar()
            print(f"✅ Total posts in database: {total_posts}")

            # Get sample post
            result = conn.execute(text("""
                SELECT post_id, creator_id, title
                FROM posts
                WHERE deleted_at IS NULL
                ORDER BY post_id DESC
                LIMIT 1
            """))
            sample = result.fetchone()

            if sample:
                print(f"   Sample post:")
                print(f"   - ID: {sample[0]}")
                print(f"   - Creator: {sample[1]}")
                print(f"   - Title: {sample[2][:50]}..." if len(sample[2]) > 50 else f"   - Title: {sample[2]}")
                return True
            else:
                print("⚠️  No posts found in database")
                return False

    except Exception as e:
        print(f"❌ Error loading posts: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_web_viewer_import():
    """Test 4: Test importing web viewer functions"""
    print("\n" + "="*60)
    print("TEST 4: Web Viewer Functions Import")
    print("="*60)

    try:
        # Add web directory to path
        sys.path.insert(0, str(Path(__file__).parent / 'web'))

        # Try to import the viewer module
        import viewer

        # Check if dual mode functions exist
        functions_to_check = [
            'use_postgresql',
            'get_database_url',
            'load_posts_from_postgres',
            'load_posts_from_json',
            'load_all_posts'
        ]

        missing = []
        for func_name in functions_to_check:
            if not hasattr(viewer, func_name):
                missing.append(func_name)

        if missing:
            print(f"❌ Missing functions: {', '.join(missing)}")
            return False
        else:
            print(f"✅ All dual mode functions present:")
            for func_name in functions_to_check:
                print(f"   - {func_name}()")
            return True

    except Exception as e:
        print(f"❌ Error importing viewer: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Web Viewer PostgreSQL Integration Tests")
    print("="*60)

    tests = [
        ("Flag Detection", test_flag_detection),
        ("Database Connection", test_database_connection),
        ("Load Posts", test_load_posts),
        ("Web Viewer Import", test_web_viewer_import)
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
        print("\n🎉 All tests passed! Web viewer PostgreSQL integration is ready!")
        print("\n📝 To use PostgreSQL mode:")
        print("   1. Ensure flag exists: touch config/use_postgresql.flag")
        print("   2. Start web viewer: python web/viewer.py")
        print("   3. Access: http://localhost:5000")
        print("\n📝 To use JSON mode:")
        print("   1. Remove flag: rm config/use_postgresql.flag")
        print("   2. Start web viewer: python web/viewer.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before using web viewer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
