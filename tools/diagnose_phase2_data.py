#!/usr/bin/env python3
"""
Diagnose Phase 2 data integrity
Compares JSON files vs PostgreSQL to find missing data
"""

import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

load_dotenv()

def get_database_url():
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

def main():
    print("=" * 80)
    print("  🔍 DIAGNOSTIC: Phase 2 Data Integrity")
    print("=" * 80)
    print()

    creator_id = 'astrobymax'

    # 1. Load JSON file
    print("📄 [1/6] Loading JSON file...")
    json_file = Path(f"data/processed/{creator_id}_posts_detailed.json")

    if not json_file.exists():
        print(f"   ❌ FAIL: JSON file not found: {json_file}")
        return False

    with open(json_file) as f:
        json_posts = json.load(f)

    print(f"   ✅ Loaded {len(json_posts)} posts from JSON")

    # Analyze JSON data
    json_with_audio = [p for p in json_posts if p.get('audios') or p.get('audio_local_paths')]
    json_with_images = [p for p in json_posts if p.get('images') or p.get('image_local_paths')]
    json_with_videos = [p for p in json_posts if p.get('videos') or p.get('video_local_paths')]

    print(f"   📊 JSON stats:")
    print(f"      - With audio: {len(json_with_audio)}")
    print(f"      - With images: {len(json_with_images)}")
    print(f"      - With videos: {len(json_with_videos)}")
    print()

    # Sample post from JSON
    sample_json = json_posts[0]
    print(f"   📋 Sample post from JSON (post_id: {sample_json.get('post_id')}):")
    print(f"      - title: {sample_json.get('title', 'N/A')[:60]}...")
    print(f"      - audios: {sample_json.get('audios', 'N/A')}")
    print(f"      - audio_local_paths: {sample_json.get('audio_local_paths', 'N/A')}")
    print(f"      - images: {len(sample_json.get('images', []))} URLs")
    print(f"      - image_local_paths: {len(sample_json.get('image_local_paths', []) if sample_json.get('image_local_paths') else [])} files")
    print(f"      - content_blocks: {len(sample_json.get('content_blocks', []))} blocks")
    print()

    # 2. Load PostgreSQL data
    print("🐘 [2/6] Loading PostgreSQL data...")
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                post_id, title,
                audios, audio_local_paths,
                images, image_local_paths,
                video_local_paths,
                content_blocks,
                patreon_tags
            FROM posts
            WHERE creator_id = :creator_id
            ORDER BY post_id
        """), {'creator_id': creator_id})

        pg_posts = [dict(row._mapping) for row in result]

    print(f"   ✅ Loaded {len(pg_posts)} posts from PostgreSQL")

    if not pg_posts:
        print(f"   ❌ FAIL: No posts found in PostgreSQL for {creator_id}")
        return False

    # Analyze PostgreSQL data
    pg_with_audio = [p for p in pg_posts if p.get('audios') or p.get('audio_local_paths')]
    pg_with_images = [p for p in pg_posts if p.get('images') or p.get('image_local_paths')]
    pg_with_videos = [p for p in pg_posts if p.get('video_local_paths')]

    print(f"   📊 PostgreSQL stats:")
    print(f"      - With audio: {len(pg_with_audio)}")
    print(f"      - With images: {len(pg_with_images)}")
    print(f"      - With videos: {len(pg_with_videos)}")
    print()

    # Sample post from PostgreSQL
    sample_pg = pg_posts[0]
    print(f"   📋 Sample post from PostgreSQL (post_id: {sample_pg.get('post_id')}):")
    print(f"      - title: {sample_pg.get('title', 'N/A')[:60] if sample_pg.get('title') else 'N/A'}...")
    print(f"      - audios: {sample_pg.get('audios')}")
    print(f"      - audio_local_paths: {sample_pg.get('audio_local_paths')}")
    print(f"      - images type: {type(sample_pg.get('images'))}")
    print(f"      - images: {sample_pg.get('images')}")
    print(f"      - image_local_paths type: {type(sample_pg.get('image_local_paths'))}")
    print(f"      - image_local_paths: {sample_pg.get('image_local_paths')}")
    print(f"      - content_blocks type: {type(sample_pg.get('content_blocks'))}")
    if sample_pg.get('content_blocks'):
        print(f"      - content_blocks: {len(sample_pg.get('content_blocks'))} blocks")
    else:
        print(f"      - content_blocks: None/Empty")
    print()

    # 3. Compare counts
    print("🔄 [3/6] Comparing JSON vs PostgreSQL...")

    if len(json_posts) != len(pg_posts):
        print(f"   ⚠️  WARNING: Post count mismatch!")
        print(f"      - JSON: {len(json_posts)} posts")
        print(f"      - PostgreSQL: {len(pg_posts)} posts")
    else:
        print(f"   ✅ Post count matches: {len(json_posts)} posts")

    print()
    print(f"   📊 Media comparison:")
    print(f"      Audio posts:")
    print(f"         - JSON: {len(json_with_audio)}")
    print(f"         - PostgreSQL: {len(pg_with_audio)}")
    print(f"         - Difference: {len(json_with_audio) - len(pg_with_audio)}")

    print(f"      Image posts:")
    print(f"         - JSON: {len(json_with_images)}")
    print(f"         - PostgreSQL: {len(pg_with_images)}")
    print(f"         - Difference: {len(json_with_images) - len(pg_with_images)}")

    print(f"      Video posts:")
    print(f"         - JSON: {len(json_with_videos)}")
    print(f"         - PostgreSQL: {len(pg_with_videos)}")
    print(f"         - Difference: {len(json_with_videos) - len(pg_with_videos)}")
    print()

    # 4. Find specific missing data
    print("🔍 [4/6] Finding posts with missing data in PostgreSQL...")

    # Create lookup by post_id
    pg_lookup = {p['post_id']: p for p in pg_posts}
    json_lookup = {p['post_id']: p for p in json_posts}

    missing_audio = []
    missing_images = []
    missing_content_blocks = []

    for post_id, json_post in json_lookup.items():
        pg_post = pg_lookup.get(post_id)

        if not pg_post:
            print(f"   ⚠️  Post {post_id} in JSON but NOT in PostgreSQL")
            continue

        # Check audio
        json_has_audio = bool(json_post.get('audios') or json_post.get('audio_local_paths'))
        pg_has_audio = bool(pg_post.get('audios') or pg_post.get('audio_local_paths'))

        if json_has_audio and not pg_has_audio:
            missing_audio.append({
                'post_id': post_id,
                'title': json_post.get('title', 'N/A')[:50],
                'json_audios': json_post.get('audios'),
                'json_audio_paths': json_post.get('audio_local_paths'),
                'pg_audios': pg_post.get('audios'),
                'pg_audio_paths': pg_post.get('audio_local_paths')
            })

        # Check images
        json_images_count = len(json_post.get('images', []) or [])
        pg_images = pg_post.get('images')

        # Handle different types for pg_images
        if pg_images is None:
            pg_images_count = 0
        elif isinstance(pg_images, list):
            pg_images_count = len(pg_images)
        elif isinstance(pg_images, str):
            # Might be a string representation
            pg_images_count = 0 if pg_images == '{}' or pg_images == '[]' else 1
        else:
            pg_images_count = 0

        if json_images_count > pg_images_count:
            missing_images.append({
                'post_id': post_id,
                'title': json_post.get('title', 'N/A')[:50],
                'json_count': json_images_count,
                'pg_count': pg_images_count,
                'json_images': json_post.get('images')[:2] if json_post.get('images') else None,
                'pg_images': pg_post.get('images')
            })

        # Check content_blocks
        json_blocks = len(json_post.get('content_blocks', []) or [])
        pg_blocks = len(pg_post.get('content_blocks', []) or []) if pg_post.get('content_blocks') else 0

        if json_blocks > 0 and pg_blocks == 0:
            missing_content_blocks.append({
                'post_id': post_id,
                'title': json_post.get('title', 'N/A')[:50],
                'json_blocks': json_blocks,
                'pg_blocks': pg_blocks
            })

    if missing_audio:
        print(f"   ⚠️  {len(missing_audio)} posts missing AUDIO in PostgreSQL:")
        for item in missing_audio[:5]:
            print(f"      - Post {item['post_id']}: {item['title']}")
            print(f"        JSON audios: {item['json_audios']}")
            print(f"        JSON paths: {item['json_audio_paths']}")
            print(f"        PG audios: {item['pg_audios']}")
            print(f"        PG paths: {item['pg_audio_paths']}")
        if len(missing_audio) > 5:
            print(f"      ... and {len(missing_audio) - 5} more")
    else:
        print(f"   ✅ All posts with audio in JSON also have audio in PostgreSQL")

    print()

    if missing_images:
        print(f"   ⚠️  {len(missing_images)} posts missing IMAGES in PostgreSQL:")
        for item in missing_images[:5]:
            print(f"      - Post {item['post_id']}: {item['title']}")
            print(f"        JSON: {item['json_count']} images")
            print(f"        PostgreSQL: {item['pg_count']} images")
            print(f"        PG images type: {type(item['pg_images'])}")
            print(f"        PG images value: {item['pg_images']}")
        if len(missing_images) > 5:
            print(f"      ... and {len(missing_images) - 5} more")
    else:
        print(f"   ✅ All posts with images in JSON also have images in PostgreSQL")

    print()

    if missing_content_blocks:
        print(f"   ⚠️  {len(missing_content_blocks)} posts missing CONTENT_BLOCKS in PostgreSQL:")
        for item in missing_content_blocks[:5]:
            print(f"      - Post {item['post_id']}: {item['title']}")
            print(f"        JSON: {item['json_blocks']} blocks")
            print(f"        PostgreSQL: {item['pg_blocks']} blocks")
        if len(missing_content_blocks) > 5:
            print(f"      ... and {len(missing_content_blocks) - 5} more")
    else:
        print(f"   ✅ All posts with content_blocks in JSON also have them in PostgreSQL")

    print()

    print()

    # 6. Check how viewer.py reads data
    print("🔍 [6/8] Checking how viewer.py reads posts for index page...")

    # Simulate what viewer.py does to get posts
    with engine.connect() as conn:
        # This is what index page does
        result = conn.execute(text("""
            SELECT
                p.post_id,
                p.title,
                p.creator_id,
                p.published_at,
                p.content_blocks,
                p.patreon_tags,
                p.audios,
                p.audio_local_paths,
                p.images,
                p.image_local_paths,
                p.video_local_paths
            FROM posts p
            WHERE p.creator_id = :creator_id
              AND p.deleted_at IS NULL
            ORDER BY p.published_at DESC
            LIMIT 5
        """), {'creator_id': creator_id})

        viewer_posts = [dict(row._mapping) for row in result]

    print(f"   ✅ Viewer query returned {len(viewer_posts)} posts (showing first 5)")
    print()

    if viewer_posts:
        print(f"   📋 How viewer sees first post:")
        vp = viewer_posts[0]
        print(f"      - post_id: {vp.get('post_id')}")
        print(f"      - title: {vp.get('title', 'N/A')[:60] if vp.get('title') else 'N/A'}...")
        print(f"      - audios type: {type(vp.get('audios'))}")
        print(f"      - audios value: {vp.get('audios')}")
        print(f"      - audio_local_paths type: {type(vp.get('audio_local_paths'))}")
        print(f"      - audio_local_paths value: {vp.get('audio_local_paths')}")
        print(f"      - images type: {type(vp.get('images'))}")
        print(f"      - images value: {vp.get('images')}")
        print(f"      - image_local_paths type: {type(vp.get('image_local_paths'))}")
        print(f"      - image_local_paths value: {vp.get('image_local_paths')}")

        # Check if viewer would consider this post as "has_audio"
        has_audio = bool(vp.get('audios') or vp.get('audio_local_paths'))
        has_images = bool(vp.get('images') or vp.get('image_local_paths'))

        print(f"      - has_audio (Python bool): {has_audio}")
        print(f"      - has_images (Python bool): {has_images}")

    print()

    # 7. Test "with audio" filter as viewer.py does it
    print("🔍 [7/8] Testing 'with audio' filter like index page does...")

    with engine.connect() as conn:
        # Test different filter conditions
        filters = {
            "audios IS NOT NULL": text("""
                SELECT COUNT(*) FROM posts
                WHERE creator_id = :creator_id AND audios IS NOT NULL
            """),
            "audio_local_paths IS NOT NULL": text("""
                SELECT COUNT(*) FROM posts
                WHERE creator_id = :creator_id AND audio_local_paths IS NOT NULL
            """),
            "audios not empty": text("""
                SELECT COUNT(*) FROM posts
                WHERE creator_id = :creator_id
                  AND audios IS NOT NULL
                  AND audios::text != '[]'
                  AND audios::text != '{}'
                  AND audios::text != ''
            """),
            "audio_local_paths not empty": text("""
                SELECT COUNT(*) FROM posts
                WHERE creator_id = :creator_id
                  AND audio_local_paths IS NOT NULL
                  AND array_length(audio_local_paths, 1) > 0
            """)
        }

        for name, query in filters.items():
            try:
                count = conn.execute(query, {'creator_id': creator_id}).scalar()
                print(f"   📊 Filter '{name}': {count} posts")
            except Exception as e:
                print(f"   ❌ Filter '{name}' FAILED: {e}")

    print()

    # 8. Check actual media files downloaded
    print("📁 [8/8] Checking downloaded media files...")

    audio_dir = Path(f"data/media/audio/{creator_id}")
    image_dir = Path(f"data/media/images/{creator_id}")
    video_dir = Path(f"data/media/videos/{creator_id}")

    audio_files = list(audio_dir.glob('*')) if audio_dir.exists() else []
    image_files = list(image_dir.glob('*')) if image_dir.exists() else []
    video_files = list(video_dir.glob('*.mp4')) if video_dir.exists() else []

    print(f"   📊 Downloaded media files:")
    print(f"      - Audio files: {len(audio_files)}")
    print(f"      - Image files: {len(image_files)}")
    print(f"      - Video files: {len(video_files)}")
    print()

    if audio_files:
        print(f"   🎵 Sample audio files:")
        for f in audio_files[:3]:
            print(f"      - {f.name}")
        if len(audio_files) > 3:
            print(f"      ... and {len(audio_files) - 3} more")

    print()

    # Summary
    print("=" * 80)
    print("  📊 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print()

    issues = []

    if len(json_posts) != len(pg_posts):
        issues.append(f"❌ Post count mismatch: JSON has {len(json_posts)}, PostgreSQL has {len(pg_posts)}")

    if missing_audio:
        issues.append(f"❌ {len(missing_audio)} posts missing audio data in PostgreSQL")

    if missing_images:
        issues.append(f"❌ {len(missing_images)} posts missing image data in PostgreSQL")

    if missing_content_blocks:
        issues.append(f"❌ {len(missing_content_blocks)} posts missing content_blocks in PostgreSQL")

    if len(json_with_audio) > 0 and audio_filter_count == 0:
        issues.append(f"❌ Audio filter returns 0 posts but JSON has {len(json_with_audio)} with audio")

    if issues:
        print("🔴 ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print()
        print("💡 LIKELY CAUSE:")
        print("   The Phase 2 UPSERT is inserting posts but NOT populating:")
        print("   - audios / audio_local_paths columns")
        print("   - images / image_local_paths columns")
        print("   - content_blocks column")
        print()
        print("   These fields might be NULL or empty arrays/objects.")
    else:
        print("✅ NO ISSUES FOUND - All data looks good!")

    print()
    return len(issues) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
