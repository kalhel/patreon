#!/usr/bin/env python3
"""
Test: Exactly what query does the settings page execute?
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
    print("  🔍 Test Settings Page Query")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    creator_id = 'astrobymax'

    print("📊 PHASE 2 QUERY (what settings page uses)")
    print("-" * 80)
    print("Query:")
    print("""
    SELECT
        COUNT(*) as total,
        MAX(updated_at) as last_updated
    FROM posts
    WHERE creator_id = :creator_id
      AND deleted_at IS NULL
      AND content_blocks IS NOT NULL
    """)
    print()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                MAX(updated_at) as last_updated
            FROM posts
            WHERE creator_id = :creator_id
              AND deleted_at IS NULL
              AND content_blocks IS NOT NULL
        """), {'creator_id': creator_id})

        row = result.fetchone()
        if row:
            print(f"Result:")
            print(f"  Total posts:    {row[0]}")
            print(f"  Last updated:   {row[1]}")
        else:
            print("  No rows returned!")

    print()
    print("=" * 80)
    print("  If this shows 77, but settings shows 80,")
    print("  then settings is falling back to JSON file")
    print("=" * 80)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
