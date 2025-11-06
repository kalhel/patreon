#!/usr/bin/env python3
"""
Add a creator to creators.json
Usage: python add_creator.py
"""
import json
import sys
from pathlib import Path

def add_creator_interactive():
    """Add a creator interactively"""
    print("="*70)
    print("ADD CREATOR TO CONFIG")
    print("="*70)
    print()

    # Get input
    creator_id = input("Creator ID (e.g., skyscript): ").strip()
    if not creator_id:
        print("❌ Creator ID is required")
        return False

    name = input("Display Name (e.g., Skyscript Astrology): ").strip()
    if not name:
        print("❌ Display name is required")
        return False

    url = input(f"Patreon URL (default: https://www.patreon.com/{creator_id}): ").strip()
    if not url:
        url = f"https://www.patreon.com/{creator_id}"

    collections_url = input(f"Collections URL (default: https://www.patreon.com/cw/{creator_id}/collections): ").strip()
    if not collections_url:
        collections_url = f"https://www.patreon.com/cw/{creator_id}/collections"

    collections_enabled_input = input("Collections enabled? (y/n, default: y): ").strip().lower()
    collections_enabled = collections_enabled_input != 'n'

    preview_color = input("Preview color (default: #4db8a0): ").strip()
    if not preview_color:
        preview_color = "#4db8a0"

    avatar = input(f"Avatar filename (default: {creator_id}.jpg): ").strip()
    if not avatar:
        avatar = f"{creator_id}.jpg"

    # Load existing creators
    config_dir = Path(__file__).parent / "config"
    creators_file = config_dir / "creators.json"

    if not creators_file.exists():
        print(f"❌ File not found: {creators_file}")
        return False

    with open(creators_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    creators_list = data.get('creators', [])

    # Check if already exists
    for creator in creators_list:
        if creator['creator_id'] == creator_id:
            print(f"❌ Creator '{creator_id}' already exists!")
            return False

    # Create new creator object
    new_creator = {
        "creator_id": creator_id,
        "name": name,
        "url": url,
        "collections_url": collections_url,
        "avatar": avatar,
        "collections_enabled": collections_enabled,
        "preview_color": preview_color
    }

    # Show preview
    print("\n" + "="*70)
    print("PREVIEW:")
    print("="*70)
    print(json.dumps(new_creator, indent=2))
    print()

    confirm = input("Add this creator? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return False

    # Add to list
    creators_list.append(new_creator)
    data['creators'] = creators_list

    # Backup original
    backup_file = creators_file.with_suffix('.json.backup')
    import shutil
    shutil.copy2(creators_file, backup_file)
    print(f"💾 Backup created: {backup_file}")

    # Save
    with open(creators_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Creator '{creator_id}' added successfully!")
    print(f"📄 File: {creators_file}")
    print()
    print("Next steps:")
    print(f"  1. python src/phase1_url_collector.py --creator {creator_id}")
    print(f"  2. python src/phase2_detail_extractor.py --creator {creator_id} --headless")
    print(f"  3. python src/phase3_collections_scraper.py --creator {creator_id} --headless")

    return True

if __name__ == "__main__":
    try:
        add_creator_interactive()
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
