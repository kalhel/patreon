#!/usr/bin/env python3
"""
Quick script to drop and recreate collections tables with correct schema
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

def get_database_url():
    """Build database URL from environment variables"""
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"

def main():
    print("🔧 Fixing collections table schema...")

    try:
        # Connect to database
        engine = create_engine(get_database_url())

        with engine.connect() as conn:
            # Drop old tables
            print("  ⏳ Dropping old collections tables...")
            conn.execute(text("DROP TABLE IF EXISTS post_collections CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS collections CASCADE"))
            conn.commit()
            print("  ✅ Old tables dropped")

            # Read and apply schema
            print("  ⏳ Applying new schema...")
            schema_file = Path('database/schema_posts.sql')

            if not schema_file.exists():
                print(f"  ❌ Schema file not found: {schema_file}")
                sys.exit(1)

            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            # Execute schema (contains multiple statements)
            conn.execute(text(schema_sql))
            conn.commit()
            print("  ✅ Schema applied successfully")

            # Verify collections table has collection_url column
            print("  ⏳ Verifying collections table structure...")
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'collections'
                AND column_name = 'collection_url'
            """))

            if result.fetchone():
                print("  ✅ collections.collection_url column verified!")
            else:
                print("  ❌ WARNING: collection_url column not found!")
                sys.exit(1)

        print("\n✅ Schema fix completed successfully!")
        print("\nNow run:")
        print("  python src/migrate_collections_to_postgres.py --skip-checks --yes")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
