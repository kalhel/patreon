#!/usr/bin/env python3
"""
Verify that posts in scraping_status actually belong to the correct creator
by checking against Patreon
"""

import os
import sys
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

load_dotenv()

def get_database_url():
    db_user = os.getenv('DB_USER', 'patreon_user')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def main():
    print("=" * 80)
    print("  🔍 Post Ownership Verification")
    print("=" * 80)
    print()

    creator_id = input("Enter creator platform_id to verify (default: astrobymax): ").strip() or "astrobymax"

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Get all post IDs for this creator
        result = conn.execute(text("""
            SELECT
                ss.post_id,
                ss.phase1_status,
                ss.phase2_status,
                ss.created_at,
                CASE WHEN p.id IS NOT NULL THEN 'YES' ELSE 'NO' END as in_posts_table
            FROM scraping_status ss
            JOIN creator_sources cs ON cs.id = ss.source_id
            LEFT JOIN posts p ON p.post_id = ss.post_id AND p.creator_id = :creator_id
            WHERE cs.platform_id = :creator_id
              AND cs.platform = 'patreon'
            ORDER BY ss.created_at DESC
        """), {'creator_id': creator_id})

        posts = []
        for row in result:
            posts.append({
                'post_id': row[0],
                'phase1': row[1],
                'phase2': row[2],
                'created_at': row[3],
                'in_posts': row[4]
            })

        print(f"Found {len(posts)} post IDs in scraping_status for '{creator_id}'")
        print()
        print("=" * 80)
        print("  📋 POST IDS TO VERIFY ON PATREON")
        print("=" * 80)
        print()
        print("Visit these URLs and verify they belong to the correct creator:")
        print()

        for i, post in enumerate(posts[:10], 1):  # Show first 10
            print(f"{i}. Post ID: {post['post_id']}")
            print(f"   URL: https://www.patreon.com/posts/{post['post_id']}")
            print(f"   Phase 1: {post['phase1']}, Phase 2: {post['phase2']}")
            print(f"   In posts table: {post['in_posts']}")
            print()

        if len(posts) > 10:
            print(f"... and {len(posts) - 10} more posts")
            print()

        print("=" * 80)
        print("  INSTRUCTIONS")
        print("=" * 80)
        print()
        print("1. Visit each URL above in your browser")
        print("2. Check if the post belongs to the correct creator")
        print("3. Note down post IDs that belong to WRONG creators")
        print("4. We'll create a cleanup script to remove them")
        print()

        # Summary
        in_posts = sum(1 for p in posts if p['in_posts'] == 'YES')
        not_in_posts = len(posts) - in_posts

        print("=" * 80)
        print("  SUMMARY")
        print("=" * 80)
        print(f"  Total URLs tracked:        {len(posts)}")
        print(f"  Posts in 'posts' table:    {in_posts}")
        print(f"  Posts NOT in 'posts' table: {not_in_posts}")
        print()
        print(f"The {not_in_posts} posts not in 'posts' table are the ones we need to verify.")
        print("If they don't belong to this creator, we should delete them.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
