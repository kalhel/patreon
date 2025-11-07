#!/usr/bin/env python3
"""Reset specific posts to pending status for re-processing"""
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

def reset_posts(post_ids):
    """Reset specific posts to pending status"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Reset posts
        update_sql = text("""
            UPDATE posts
            SET status = 'pending',
                details_extracted = false,
                attempt_count = 0
            WHERE post_id = ANY(:post_ids)
        """)

        conn.execute(update_sql, {'post_ids': post_ids})
        conn.commit()

        print(f"✅ Reset {len(post_ids)} posts to pending status")

        # Verify
        verify_sql = text("""
            SELECT post_id, title, status, details_extracted, attempt_count
            FROM posts
            WHERE post_id = ANY(:post_ids)
        """)

        result = conn.execute(verify_sql, {'post_ids': post_ids})
        rows = result.fetchall()

        print(f"\n{'='*70}")
        print("RESET POSTS:")
        print(f"{'='*70}\n")

        for row in rows:
            print(f"Post ID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Status: {row[2]}")
            print(f"Details Extracted: {row[3]}")
            print(f"Attempt Count: {row[4]}")
            print()

if __name__ == "__main__":
    # Posts with image display issues
    post_ids = ['111538285', '141080275', '113258529']
    reset_posts(post_ids)
