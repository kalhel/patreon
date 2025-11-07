#!/usr/bin/env python3
"""Debug specific post to see all its data"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
import json
import os
from urllib.parse import quote_plus

def get_database_url():
    """Build PostgreSQL connection URL from env vars"""
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    db_password_encoded = quote_plus(db_password)
    return f"postgresql://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"

def debug_post(post_id):
    """Show all data for a specific post"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        query = text("""
            SELECT
                post_id,
                creator_id,
                title,
                full_content,
                image_local_paths,
                video_local_paths,
                audio_local_paths,
                images,
                videos,
                audios,
                content_blocks,
                post_metadata,
                published_at,
                created_at
            FROM posts
            WHERE post_id = :post_id
        """)

        result = conn.execute(query, {'post_id': post_id})
        row = result.fetchone()

        if not row:
            print(f"❌ Post {post_id} not found in database")
            return

        print(f"\n{'='*70}")
        print(f"POST DATA FOR: {post_id}")
        print(f"{'='*70}\n")

        print(f"Creator ID: {row[1]}")
        print(f"Title: {row[2]}")
        print(f"Full Content Length: {len(row[3]) if row[3] else 0} characters")
        print(f"Published At: {row[12]}")
        print(f"Created At: {row[13]}")
        print()

        print(f"{'='*70}")
        print(f"LOCAL MEDIA PATHS (Downloaded Files)")
        print(f"{'='*70}\n")

        image_paths = row[4]
        video_paths = row[5]
        audio_paths = row[6]

        print(f"image_local_paths (type={type(image_paths)}):")
        if image_paths:
            print(f"  Count: {len(image_paths)}")
            for i, path in enumerate(image_paths, 1):
                print(f"  [{i}] {path}")
                # Check if file exists
                file_path = Path(__file__).parent / "data" / "media" / path
                exists = file_path.exists()
                print(f"      File exists: {'✅' if exists else '❌'}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"video_local_paths (type={type(video_paths)}):")
        if video_paths:
            print(f"  Count: {len(video_paths)}")
            for i, path in enumerate(video_paths, 1):
                print(f"  [{i}] {path}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"audio_local_paths (type={type(audio_paths)}):")
        if audio_paths:
            print(f"  Count: {len(audio_paths)}")
            for i, path in enumerate(audio_paths, 1):
                print(f"  [{i}] {path}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"{'='*70}")
        print(f"REMOTE MEDIA URLS (Original Patreon URLs)")
        print(f"{'='*70}\n")

        images = row[7]
        videos = row[8]
        audios = row[9]

        print(f"images (type={type(images)}):")
        if images:
            print(f"  Count: {len(images)}")
            for i, url in enumerate(images, 1):
                print(f"  [{i}] {url[:80]}...")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"videos (type={type(videos)}):")
        if videos:
            print(f"  Count: {len(videos)}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"audios (type={type(audios)}):")
        if audios:
            print(f"  Count: {len(audios)}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"{'='*70}")
        print(f"CONTENT BLOCKS")
        print(f"{'='*70}\n")

        content_blocks = row[10]
        if content_blocks:
            print(f"Type: {type(content_blocks)}")
            print(f"Count: {len(content_blocks)}")
            print(f"\nBlock types present:")
            block_types = {}
            for block in content_blocks:
                if isinstance(block, dict):
                    btype = block.get('type', 'unknown')
                    block_types[btype] = block_types.get(btype, 0) + 1

            for btype, count in block_types.items():
                print(f"  - {btype}: {count}")

            print(f"\nFirst 3 blocks:")
            for i, block in enumerate(content_blocks[:3], 1):
                if isinstance(block, dict):
                    print(f"  [{i}] Type: {block.get('type')}, Order: {block.get('order')}")
                    if block.get('type') == 'heading_1':
                        print(f"      Text: {block.get('text', '')[:100]}")
                    elif block.get('type') == 'image':
                        print(f"      Media ID: {block.get('media_id')}")
                        print(f"      URL: {block.get('url', '')[:80]}")
        else:
            print(f"  ⚠️  EMPTY or NULL")
        print()

        print(f"{'='*70}")
        print(f"POST METADATA")
        print(f"{'='*70}\n")

        metadata = row[11]
        if metadata:
            print(f"Type: {type(metadata)}")
            print(f"Keys: {list(metadata.keys())}")
            if 'published_date' in metadata:
                print(f"published_date: {metadata['published_date']}")
            if 'creator_name' in metadata:
                print(f"creator_name: {metadata['creator_name']}")
        else:
            print(f"  ⚠️  EMPTY or NULL")

if __name__ == "__main__":
    import sys
    post_id = sys.argv[1] if len(sys.argv) > 1 else '111538285'
    debug_post(post_id)
