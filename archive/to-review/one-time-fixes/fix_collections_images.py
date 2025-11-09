#!/usr/bin/env python3
"""
Fix Collections Images - Add image fields and populate from JSON
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def get_database_url():
    """Build PostgreSQL connection URL"""
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'alejandria')

    if not db_password:
        raise ValueError("DB_PASSWORD not found in .env")

    encoded_password = quote_plus(db_password)
    return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def add_image_columns():
    """Add image columns to collections table if they don't exist"""
    print("\n" + "="*60)
    print("STEP 1: Adding image columns to collections table")
    print("="*60)

    engine = create_engine(get_database_url())

    try:
        with engine.connect() as conn:
            # Check if columns exist
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'collections'
                AND column_name IN ('collection_image', 'collection_image_local')
            """)
            result = conn.execute(check_sql)
            existing_cols = {row[0] for row in result.fetchall()}

            # Add collection_image if missing
            if 'collection_image' not in existing_cols:
                print("  Adding column: collection_image")
                conn.execute(text("""
                    ALTER TABLE collections
                    ADD COLUMN collection_image TEXT
                """))
                conn.commit()
                print("  ✅ Added collection_image")
            else:
                print("  ⏭️  Column collection_image already exists")

            # Add collection_image_local if missing
            if 'collection_image_local' not in existing_cols:
                print("  Adding column: collection_image_local")
                conn.execute(text("""
                    ALTER TABLE collections
                    ADD COLUMN collection_image_local TEXT
                """))
                conn.commit()
                print("  ✅ Added collection_image_local")
            else:
                print("  ⏭️  Column collection_image_local already exists")

        print("\n✅ Image columns ready!")
        return True

    except Exception as e:
        print(f"\n❌ Error adding columns: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def update_collections_from_json():
    """Update collections with image data from JSON files"""
    print("\n" + "="*60)
    print("STEP 2: Updating collections with image data from JSON")
    print("="*60)

    engine = create_engine(get_database_url())

    # Find all collections JSON files
    json_files = []

    # Check data/backups directory
    backup_dir = Path("data/backups")
    if backup_dir.exists():
        for creator_dir in backup_dir.iterdir():
            if creator_dir.is_dir():
                for json_file in creator_dir.glob("*_collections.json"):
                    json_files.append(json_file)

    print(f"\n📂 Found {len(json_files)} collections JSON files")

    if not json_files:
        print("⚠️  No collections JSON files found")
        return False

    updated_count = 0
    skipped_count = 0

    try:
        with engine.connect() as conn:
            for json_file in json_files:
                print(f"\n  Processing: {json_file.name}")

                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                creator_id = data.get('creator_id')
                collections = data.get('collections', [])

                print(f"    Creator: {creator_id}")
                print(f"    Collections: {len(collections)}")

                for coll in collections:
                    collection_id = coll.get('collection_id')
                    collection_image = coll.get('collection_image')
                    collection_image_local = coll.get('collection_image_local')

                    # Update in database
                    update_sql = text("""
                        UPDATE collections
                        SET
                            collection_image = :image,
                            collection_image_local = :image_local
                        WHERE collection_id = :id
                    """)

                    result = conn.execute(update_sql, {
                        'id': collection_id,
                        'image': collection_image,
                        'image_local': collection_image_local
                    })

                    if result.rowcount > 0:
                        updated_count += 1
                        print(f"      ✅ Updated collection {collection_id}")
                    else:
                        skipped_count += 1
                        print(f"      ⏭️  Collection {collection_id} not found in DB")

            conn.commit()

        print(f"\n📊 Summary:")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"\n✅ Collections updated successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error updating collections: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def verify_images():
    """Verify that collections now have images"""
    print("\n" + "="*60)
    print("STEP 3: Verification")
    print("="*60)

    engine = create_engine(get_database_url())

    try:
        with engine.connect() as conn:
            # Count collections with images
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(collection_image) as with_remote_image,
                    COUNT(collection_image_local) as with_local_image
                FROM collections
                WHERE deleted_at IS NULL
            """))

            row = result.fetchone()
            total = row[0]
            with_remote = row[1]
            with_local = row[2]

            print(f"\n📊 Collections Statistics:")
            print(f"  Total collections: {total}")
            print(f"  With remote image: {with_remote}")
            print(f"  With local image:  {with_local}")

            if with_local > 0:
                print(f"\n✅ Collections have images! ({with_local}/{total})")
                return True
            else:
                print(f"\n⚠️  No collections have images yet")
                return False

    except Exception as e:
        print(f"\n❌ Error verifying: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("🖼️  Collections Images Fix")
    print("="*60)

    # Step 1: Add columns
    if not add_image_columns():
        print("\n❌ Failed to add columns. Exiting.")
        return 1

    # Step 2: Update from JSON
    if not update_collections_from_json():
        print("\n⚠️  Failed to update collections from JSON")
        print("   (This is OK if collections already have images)")

    # Step 3: Verify
    verify_images()

    print("\n" + "="*60)
    print("✅ DONE! Collections images fix complete")
    print("="*60)
    print("\nNext step: Restart web viewer to see collection images")

    return 0


if __name__ == "__main__":
    sys.exit(main())
