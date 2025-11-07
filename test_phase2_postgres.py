#!/usr/bin/env python3
"""
Test script for Phase 2 PostgreSQL integration
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from datetime import datetime
import json

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


def test_posts_table():
    """Test 3: Check posts table exists and has data"""
    print("\n" + "="*60)
    print("TEST 3: Posts Table")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'posts'
            """))
            exists = result.scalar() > 0

            if exists:
                # Get count
                result = conn.execute(text("SELECT COUNT(*) FROM posts"))
                count = result.scalar()
                print(f"✅ Posts table exists")
                print(f"   Current count: {count} posts")

                # Check posts needing details
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM posts
                    WHERE status->>'details_extracted' = 'false'
                    OR status->>'details_extracted' IS NULL
                """))
                pending = result.scalar()
                print(f"   Posts needing details: {pending}")

                return True
            else:
                print("❌ Posts table does NOT exist")
                return False

    except Exception as e:
        print(f"❌ Error checking posts table: {e}")
        return False


def test_update_post_details():
    """Test 4: Update a test post with sample details"""
    print("\n" + "="*60)
    print("TEST 4: Update Post Details")
    print("="*60)

    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Find a post to test with
            result = conn.execute(text("SELECT post_id FROM posts LIMIT 1"))
            row = result.fetchone()

            if not row:
                print("❌ No posts found in database to test with")
                return False

            test_post_id = row[0]
            print(f"   Testing with post: {test_post_id}")

            # Prepare test data
            test_content_blocks = [
                {"type": "text", "text": "Test content block from Phase 2 test"},
                {"type": "image", "url": "https://example.com/test.jpg"}
            ]
            test_video_streams = [
                {
                    "quality": "720p",
                    "url": "https://example.com/video.m3u8",
                    "type": "hls"
                }
            ]

            # Update the post
            update_sql = text("""
                UPDATE posts
                SET
                    title = :title,
                    content = :content,
                    content_blocks = CAST(:content_blocks AS jsonb),
                    video_streams = CAST(:video_streams AS jsonb),
                    images = :images,
                    patreon_tags = :patreon_tags,
                    updated_at = NOW()
                WHERE post_id = :post_id
            """)

            conn.execute(update_sql, {
                'post_id': test_post_id,
                'title': 'Test Post - Phase 2 PostgreSQL Integration',
                'content': 'This is test content to verify PostgreSQL updates work correctly.',
                'content_blocks': json.dumps(test_content_blocks),
                'video_streams': json.dumps(test_video_streams),
                'images': ['https://example.com/test1.jpg', 'https://example.com/test2.jpg'],
                'patreon_tags': ['test', 'phase2', 'postgresql']
            })
            conn.commit()

            print("✅ Post updated successfully")

            # Verify the update
            verify_sql = text("""
                SELECT title, content, content_blocks, images, patreon_tags
                FROM posts
                WHERE post_id = :id
            """)
            result = conn.execute(verify_sql, {'id': test_post_id})
            updated_post = result.fetchone()

            print(f"   Title: {updated_post[0]}")
            print(f"   Content blocks: {len(updated_post[2])} blocks")
            print(f"   Images: {len(updated_post[3])} images")
            print(f"   Tags: {len(updated_post[4])} tags")

            return True

    except Exception as e:
        print(f"❌ Error updating post: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Phase 2 PostgreSQL Integration Tests")
    print("="*60)

    tests = [
        ("Flag Detection", test_flag_detection),
        ("Database Connection", test_database_connection),
        ("Posts Table", test_posts_table),
        ("Update Post Details", test_update_post_details)
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
        print("\n🎉 All tests passed! Phase 2 PostgreSQL integration is ready!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before using Phase 2 scraper.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
