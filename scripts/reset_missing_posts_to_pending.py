#!/usr/bin/env python3
"""
Reset 3 missing posts to phase2_status='pending' so Phase 2 can reprocess them
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
    print("  🔄 Reset Missing Posts to Pending")
    print("=" * 80)
    print()

    missing_post_ids = ['96097452', '77933294', '42294201']

    print("Posts to reset:")
    for post_id in missing_post_ids:
        print(f"  - {post_id}")
    print()

    response = input("Reset these posts to phase2_status='pending'? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted by user")
        return 0

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.begin() as conn:
        print()
        print("🔄 Resetting posts...")

        for post_id in missing_post_ids:
            result = conn.execute(text("""
                UPDATE scraping_status
                SET phase2_status = 'pending',
                    updated_at = NOW()
                WHERE post_id = :post_id
            """), {'post_id': post_id})

            print(f"  ✅ Reset {post_id} to pending")

        print()
        print("=" * 80)
        print("  ✅ RESET COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Re-run Phase 2 scraper for AstroByMax")
        print("  2. It will process only the 3 pending posts")
        print("  3. Verify they appear in posts table after processing")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
