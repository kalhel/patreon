#!/usr/bin/env python3
"""
Quick check: What columns do posts have and what's populated?
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
    print("  🔍 Posts Content Check - AstroByMax")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Check what columns exist in posts table
        print("📊 POSTS TABLE COLUMNS")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'posts'
            ORDER BY ordinal_position
        """))

        for row in result:
            print(f"  {row[0]:<30} {row[1]:<20} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")
        print()

        # Check content columns for AstroByMax
        print("📊 CONTENT STATUS FOR ASTROBYMAX")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as with_title,
                COUNT(CASE WHEN content IS NOT NULL AND content != '' THEN 1 END) as with_content,
                COUNT(CASE WHEN full_content IS NOT NULL AND full_content != '' THEN 1 END) as with_full_content,
                COUNT(CASE WHEN content_blocks IS NOT NULL THEN 1 END) as with_content_blocks
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND deleted_at IS NULL
        """))

        row = result.fetchone()
        if row:
            print(f"  Total posts:               {row[0]}")
            print(f"  Posts with title:          {row[1]}")
            print(f"  Posts with content:        {row[2]}")
            print(f"  Posts with full_content:   {row[3]}")
            print(f"  Posts with content_blocks: {row[4]}")
        print()

        # Show a sample post to see what data it has
        print("📊 SAMPLE POST DATA (first post)")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT
                post_id,
                title,
                CASE
                    WHEN content IS NOT NULL AND content != '' THEN LENGTH(content)
                    ELSE 0
                END as content_length,
                CASE
                    WHEN full_content IS NOT NULL AND full_content != '' THEN LENGTH(full_content)
                    ELSE 0
                END as full_content_length,
                created_at,
                updated_at
            FROM posts
            WHERE creator_id = 'astrobymax'
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """))

        row = result.fetchone()
        if row:
            print(f"  Post ID:             {row[0]}")
            print(f"  Title:               {row[1][:50] if row[1] else 'NULL'}...")
            print(f"  content length:      {row[2]} chars")
            print(f"  full_content length: {row[3]} chars")
            print(f"  Created:             {row[4]}")
            print(f"  Updated:             {row[5]}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
