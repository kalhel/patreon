#!/usr/bin/env python3
"""Reset all posts from a creator to pending status for re-processing"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
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

def reset_creator_posts(creator_id):
    """Reset all posts from a creator to pending status"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # First, show what will be reset
        count_sql = text("""
            SELECT COUNT(*) FROM posts
            WHERE creator_id = :creator_id
        """)
        result = conn.execute(count_sql, {'creator_id': creator_id})
        total = result.fetchone()[0]

        print(f"Found {total} posts for creator '{creator_id}'")

        if total == 0:
            print("No posts found!")
            return

        # Reset posts
        update_sql = text("""
            UPDATE posts
            SET status = 'pending',
                details_extracted = false,
                attempt_count = 0
            WHERE creator_id = :creator_id
        """)

        conn.execute(update_sql, {'creator_id': creator_id})
        conn.commit()

        print(f"✅ Reset {total} posts to pending status for creator '{creator_id}'")

        # Show sample
        verify_sql = text("""
            SELECT post_id, title, status, details_extracted
            FROM posts
            WHERE creator_id = :creator_id
            ORDER BY post_id DESC
            LIMIT 5
        """)

        result = conn.execute(verify_sql, {'creator_id': creator_id})
        rows = result.fetchall()

        print(f"\n{'='*70}")
        print(f"SAMPLE OF RESET POSTS (showing first 5):")
        print(f"{'='*70}\n")

        for row in rows:
            print(f"Post ID: {row[0]}")
            print(f"Title: {row[1][:60]}..." if row[1] and len(row[1]) > 60 else f"Title: {row[1]}")
            print(f"Status: {row[2]}")
            print(f"Details Extracted: {row[3]}")
            print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 reset_creator_posts.py <creator_id>")
        print("Example: python3 reset_creator_posts.py astrobymax")
        sys.exit(1)

    creator_id = sys.argv[1]
    reset_creator_posts(creator_id)
