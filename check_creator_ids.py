#!/usr/bin/env python3
"""Check and fix creator_id for specific posts"""
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

def check_posts():
    """Check creator_id for problematic posts"""
    engine = create_engine(get_database_url())

    problematic_posts = ['96097452', '77933294', '42294201']

    with engine.connect() as conn:
        query = text("""
            SELECT post_id, creator_id, title, post_url, creator_name
            FROM posts
            WHERE post_id IN :post_ids
        """)

        result = conn.execute(query, {'post_ids': tuple(problematic_posts)})
        rows = result.fetchall()

        print(f"\n{'='*70}")
        print(f"POSTS THAT APPEAR IN ASTROBYMAX FILTER")
        print(f"{'='*70}\n")

        for row in rows:
            print(f"Post ID: {row[0]}")
            print(f"Creator ID: {row[1]}")
            print(f"Creator Name: {row[4]}")
            print(f"Title: {row[2]}")
            print(f"URL: {row[3]}")
            print()

        # Extract the correct creator_id from the URL
        print(f"\n{'='*70}")
        print(f"CORRECT CREATOR IDs FROM URLs")
        print(f"{'='*70}\n")

        fixes = []
        for row in rows:
            post_id = row[0]
            current_creator = row[1]
            post_url = row[3]

            if post_url and 'patreon.com/' in post_url:
                # Extract creator from URL: https://www.patreon.com/posts/CREATOR/POST_ID
                parts = post_url.split('patreon.com/')
                if len(parts) > 1:
                    # URL format: https://www.patreon.com/posts/title-123456
                    # The creator_id should come from creator_sources table
                    # Let's check what creator_sources says

                    # For now, just report
                    print(f"Post {post_id}: current='{current_creator}', URL={post_url}")
                    fixes.append((post_id, current_creator, post_url))

        # Now determine correct creator_id based on creator_name
        print(f"\n{'='*70}")
        print(f"DETERMINING CORRECT CREATOR_ID FROM CREATOR_NAME")
        print(f"{'='*70}\n")

        # Mapping of creator names to their correct creator_id
        creator_name_mapping = {
            'Ali A Olomi': 'headonhistory',
            'HOROI Project': 'horoiproject',
            'AstroByMax': 'astrobymax'
        }

        sql_fixes = []
        for row in rows:
            post_id = row[0]
            current_creator_id = row[1]
            creator_name = row[4]

            correct_creator_id = creator_name_mapping.get(creator_name)

            print(f"Post {post_id}:")
            print(f"  Current creator_id: '{current_creator_id}'")
            print(f"  Creator name: '{creator_name}'")
            print(f"  Correct creator_id: '{correct_creator_id}'")

            if correct_creator_id and current_creator_id != correct_creator_id:
                print(f"  ❌ MISMATCH!")
                sql_fixes.append(f"UPDATE posts SET creator_id = '{correct_creator_id}' WHERE post_id = '{post_id}';")
            else:
                print(f"  ✅ OK")
            print()

        if sql_fixes:
            print(f"\n{'='*70}")
            print(f"SQL FIX SCRIPT")
            print(f"{'='*70}\n")
            for fix in sql_fixes:
                print(fix)
            print()
            print("Run these commands with:")
            print("  psql -d alejandria -c \"<SQL_COMMAND>\"")
            print("Or save to a file and run: psql -d alejandria -f fix_creator_ids.sql")

if __name__ == "__main__":
    check_posts()
