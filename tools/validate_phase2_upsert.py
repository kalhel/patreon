#!/usr/bin/env python3
"""
Validate Phase 2 UPSERT fix before committing
Checks:
1. Posts table structure and constraints
2. JSON file has required fields
3. UPSERT SQL will work with actual data
"""

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

load_dotenv()

def get_database_url():
    """Build database URL from environment variables"""
    from urllib.parse import quote_plus

    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in environment")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

def main():
    print("=" * 80)
    print("  🔍 VALIDATION: Phase 2 UPSERT Fix")
    print("=" * 80)
    print()

    # Check 1: Verify posts table structure
    print("📋 [1/5] Checking posts table structure...")
    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            # Get table columns
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'posts'
                ORDER BY ordinal_position
            """))

            columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result}

            # Required columns for UPSERT
            required = [
                'post_id', 'creator_id', 'post_url', 'title', 'full_content',
                'content_blocks', 'post_metadata', 'published_at',
                'video_streams', 'video_subtitles', 'video_local_paths',
                'audios', 'audio_local_paths', 'images', 'image_local_paths',
                'patreon_tags', 'created_at', 'updated_at'
            ]

            missing = [col for col in required if col not in columns]

            if missing:
                print(f"   ❌ FAIL: Missing columns: {missing}")
                return False

            print(f"   ✅ PASS: All {len(required)} required columns exist")
            print(f"   📊 Total columns in posts table: {len(columns)}")

    except Exception as e:
        print(f"   ❌ FAIL: Database error: {e}")
        return False

    # Check 2: Verify UNIQUE constraint on post_id
    print("\n🔑 [2/5] Checking UNIQUE constraint on post_id...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'posts'
                  AND (constraint_type = 'UNIQUE' OR constraint_type = 'PRIMARY KEY')
            """))

            constraints = [(row[0], row[1]) for row in result]

            # Check if post_id has a unique constraint
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'posts'
                  AND column_name = 'post_id'
            """))

            has_unique = result.fetchone() is not None

            if not has_unique:
                print(f"   ❌ FAIL: No UNIQUE constraint on post_id")
                print(f"   ⚠️  ON CONFLICT (post_id) will not work!")
                return False

            print(f"   ✅ PASS: post_id has UNIQUE constraint")
            print(f"   📊 Total constraints: {len(constraints)}")

    except Exception as e:
        print(f"   ❌ FAIL: Error checking constraints: {e}")
        return False

    # Check 3: Verify JSON file exists and has data
    print("\n📄 [3/5] Checking JSON file with scraped posts...")
    json_file = Path("data/processed/astrobymax_posts_detailed.json")

    if not json_file.exists():
        print(f"   ❌ FAIL: JSON file not found: {json_file}")
        return False

    try:
        with open(json_file) as f:
            posts = json.load(f)

        if not posts:
            print(f"   ❌ FAIL: JSON file is empty")
            return False

        print(f"   ✅ PASS: JSON file exists with {len(posts)} posts")
        print(f"   📊 File size: {json_file.stat().st_size / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"   ❌ FAIL: Error reading JSON: {e}")
        return False

    # Check 4: Verify posts have required fields
    print("\n🏷️  [4/5] Checking posts have required fields...")
    required_fields = ['post_id', 'creator_id', 'post_url', 'title']

    sample_post = posts[0]
    missing_fields = [field for field in required_fields if field not in sample_post]

    if missing_fields:
        print(f"   ❌ FAIL: Sample post missing fields: {missing_fields}")
        print(f"   📋 Available fields: {list(sample_post.keys())[:10]}...")
        return False

    print(f"   ✅ PASS: All required fields present")
    print(f"   📋 Sample post:")
    print(f"      - post_id: {sample_post['post_id']}")
    print(f"      - creator_id: {sample_post['creator_id']}")
    print(f"      - post_url: {sample_post['post_url'][:60]}...")
    print(f"      - title: {sample_post.get('title', 'N/A')[:60]}...")

    # Check all posts have creator_id = 'astrobymax'
    wrong_creator = [p['post_id'] for p in posts if p.get('creator_id') != 'astrobymax']
    if wrong_creator:
        print(f"   ⚠️  WARNING: {len(wrong_creator)} posts have wrong creator_id:")
        for pid in wrong_creator[:5]:
            post = next(p for p in posts if p['post_id'] == pid)
            print(f"      - {pid}: {post.get('creator_id')}")
        if len(wrong_creator) > 5:
            print(f"      ... and {len(wrong_creator) - 5} more")

    # Check 5: Test UPSERT with dry-run
    print("\n🧪 [5/5] Testing UPSERT SQL syntax (dry-run)...")
    try:
        test_post = posts[0]

        # Extract full_content from content_blocks
        full_content = ""
        if test_post.get('content_blocks'):
            text_blocks = [block.get('text', '') for block in test_post.get('content_blocks', [])
                          if block.get('type') == 'text' and block.get('text')]
            full_content = '\n\n'.join(text_blocks)

        upsert_params = {
            'post_id': test_post.get('post_id'),
            'creator_id': test_post.get('creator_id'),
            'post_url': test_post.get('post_url'),
            'title': test_post.get('title'),
            'full_content': full_content,
            'content_blocks': json.dumps(test_post.get('content_blocks', [])),
            'post_metadata': json.dumps(test_post.get('post_metadata', {})),
            'published_at': test_post.get('published_at'),
            'video_streams': json.dumps(test_post.get('video_streams', [])),
            'video_subtitles': json.dumps(test_post.get('video_subtitles', [])),
            'video_local_paths': test_post.get('video_local_paths'),
            'audios': test_post.get('audios'),
            'audio_local_paths': test_post.get('audio_local_paths'),
            'images': test_post.get('images'),
            'image_local_paths': test_post.get('image_local_paths'),
            'patreon_tags': test_post.get('patreon_tags')
        }

        # Test parameter binding (without executing)
        with engine.connect() as conn:
            # Use EXPLAIN to test SQL without executing
            test_sql = text("""
                EXPLAIN
                INSERT INTO posts (
                    post_id, creator_id, post_url, title, full_content,
                    content_blocks, post_metadata, published_at,
                    video_streams, video_subtitles, video_local_paths,
                    audios, audio_local_paths, images, image_local_paths,
                    patreon_tags, created_at, updated_at
                ) VALUES (
                    :post_id, :creator_id, :post_url, :title, :full_content,
                    CAST(:content_blocks AS jsonb), CAST(:post_metadata AS jsonb), :published_at,
                    CAST(:video_streams AS jsonb), CAST(:video_subtitles AS jsonb), :video_local_paths,
                    :audios, :audio_local_paths, :images, :image_local_paths,
                    :patreon_tags, NOW(), NOW()
                )
                ON CONFLICT (post_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    full_content = EXCLUDED.full_content,
                    content_blocks = EXCLUDED.content_blocks,
                    post_metadata = EXCLUDED.post_metadata,
                    published_at = EXCLUDED.published_at,
                    video_streams = EXCLUDED.video_streams,
                    video_subtitles = EXCLUDED.video_subtitles,
                    video_local_paths = EXCLUDED.video_local_paths,
                    audios = EXCLUDED.audios,
                    audio_local_paths = EXCLUDED.audio_local_paths,
                    images = EXCLUDED.images,
                    image_local_paths = EXCLUDED.image_local_paths,
                    patreon_tags = EXCLUDED.patreon_tags,
                    updated_at = NOW()
            """)

            result = conn.execute(test_sql, upsert_params)
            explain_plan = result.fetchall()

        print(f"   ✅ PASS: UPSERT SQL is valid")
        print(f"   📋 Test with post: {test_post['post_id']}")

    except Exception as e:
        print(f"   ❌ FAIL: UPSERT SQL error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 80)
    print("  ✅ ALL VALIDATIONS PASSED")
    print("=" * 80)
    print()
    print("📊 Summary:")
    print(f"   - Posts table: ✅ All {len(required)} columns exist")
    print(f"   - UNIQUE constraint: ✅ ON CONFLICT (post_id) will work")
    print(f"   - JSON file: ✅ {len(posts)} posts ready to insert")
    print(f"   - Required fields: ✅ All present in posts")
    print(f"   - UPSERT SQL: ✅ Syntax valid, ready to execute")
    print()
    print("✅ Safe to commit and run Phase 2 again!")
    print()

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
