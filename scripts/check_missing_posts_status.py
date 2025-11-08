#!/usr/bin/env python3
"""
Check the exact status of the 3 missing posts in scraping_status
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
    print("  🔍 Status of 3 Missing Posts in scraping_status")
    print("=" * 80)
    print()

    db_url = get_database_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    missing_post_ids = ['96097452', '77933294', '42294201']

    with engine.connect() as conn:
        print("📊 SCRAPING_STATUS for missing posts")
        print("-" * 80)

        for post_id in missing_post_ids:
            result = conn.execute(text("""
                SELECT
                    ss.post_id,
                    ss.phase1_status,
                    ss.phase2_status,
                    ss.created_at,
                    ss.updated_at
                FROM scraping_status ss
                JOIN creator_sources cs ON cs.id = ss.source_id
                WHERE ss.post_id = :post_id
                  AND cs.platform_id = 'astrobymax'
            """), {'post_id': post_id})

            row = result.fetchone()
            if row:
                print(f"Post ID: {row[0]}")
                print(f"  phase1_status: {row[1]}")
                print(f"  phase2_status: {row[2]}")
                print(f"  created_at:    {row[3]}")
                print(f"  updated_at:    {row[4]}")
                print()
            else:
                print(f"❌ Post ID {post_id} not found in scraping_status!")
                print()

        # Summary
        print("=" * 80)
        print("  💡 ANÁLISIS")
        print("=" * 80)
        print()
        print("Si phase2_status = 'completed' pero el post no existe en posts table:")
        print("  → El estado está INCORRECTO, debería ser 'pending' o similar")
        print()
        print("Si phase2_status = 'pending':")
        print("  → El estado es correcto, solo falta procesar estos posts")
        print()
        print("SOLUCIÓN:")
        print("  1. Si los post_ids aún existen en Patreon, re-ejecutar Phase 2")
        print("  2. Si los posts fueron borrados de Patreon, marcarlos como deleted")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
