#!/usr/bin/env python3
"""Debug script to check post data in PostgreSQL"""
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

    # URL-encode password to handle special characters
    db_password_encoded = quote_plus(db_password)

    return f"postgresql://{db_user}:{db_password_encoded}@{db_host}:{db_port}/{db_name}"

def check_post(post_id):
    """Check post data in PostgreSQL"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        query = text("""
            SELECT
                post_id,
                creator_id,
                title,
                image_local_paths,
                video_local_paths,
                audio_local_paths,
                video_subtitles,
                content_blocks
            FROM posts
            WHERE post_id = :post_id
        """)

        result = conn.execute(query, {'post_id': post_id})
        row = result.fetchone()

        if not row:
            print(f"❌ Post {post_id} not found")
            return

        print(f"\n{'='*70}")
        print(f"POST: {post_id}")
        print(f"{'='*70}\n")

        print(f"Creator ID: {row[1]}")
        print(f"Title: {row[2]}\n")

        print(f"image_local_paths type: {type(row[3])}")
        print(f"image_local_paths value: {row[3]}")
        print(f"image_local_paths length: {len(row[3]) if row[3] else 0}\n")

        print(f"video_local_paths type: {type(row[4])}")
        print(f"video_local_paths value: {row[4]}")
        print(f"video_local_paths length: {len(row[4]) if row[4] else 0}\n")

        print(f"audio_local_paths type: {type(row[5])}")
        print(f"audio_local_paths value: {row[5]}")
        print(f"audio_local_paths length: {len(row[5]) if row[5] else 0}\n")

        print(f"video_subtitles type: {type(row[6])}")
        print(f"video_subtitles value: {row[6][:200] if row[6] else None}...\n")

        print(f"content_blocks type: {type(row[7])}")
        if row[7]:
            blocks = row[7]
            print(f"content_blocks length: {len(blocks)}")
            print(f"Block types: {[b.get('type') for b in blocks if isinstance(b, dict)]}")

if __name__ == "__main__":
    # Check the three problematic posts
    posts_to_check = ['111538285', '141080275', '113258529']

    for post_id in posts_to_check:
        check_post(post_id)
        print("\n")
