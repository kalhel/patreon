#!/usr/bin/env python3
"""
Debug script to understand why only 1 of 2 attachments was downloaded for post 139945403
"""

import psycopg2
import json
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv

def main():
    load_dotenv()

    print("=" * 80)
    print("DEBUG: Why was only 1 attachment downloaded for post 139945403?")
    print("=" * 80)
    print()

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'alejandria'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT attachments, attachment_local_paths
        FROM posts
        WHERE post_id = '139945403'
    """)

    row = cursor.fetchone()
    attachments_json, attachment_local_json = row

    # Parse JSON
    if isinstance(attachments_json, str):
        attachments = json.loads(attachments_json)
    else:
        attachments = attachments_json

    if isinstance(attachment_local_json, str):
        attachment_local = json.loads(attachment_local_json)
    else:
        attachment_local = attachment_local_json

    print("SQL Data:")
    print(f"  Attachments in SQL: {len(attachments)}")
    print(f"  Downloaded files:   {len(attachment_local)}")
    print()

    # Show both attachments
    print("Attachments that should have been downloaded:")
    for i, att in enumerate(attachments):
        url = att.get('url', '')
        filename = att.get('filename', 'N/A')
        media_id = url.split('&m=')[1].split('&')[0] if '&m=' in url else 'N/A'
        print(f"  {i}. {filename}")
        print(f"     URL: {url}")
        print(f"     Media ID: {media_id}")
        print()

    # Check downloaded file
    print("Downloaded file:")
    if attachment_local:
        downloaded_path = Path('data/media') / attachment_local[0]
        print(f"  Path: {downloaded_path}")
        if downloaded_path.exists():
            size = downloaded_path.stat().st_size
            print(f"  Size: {size:,} bytes ({size/1024/1024:.2f} MB)")

            # Calculate hash
            with open(downloaded_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            print(f"  Hash: {file_hash}")
        else:
            print("  File does not exist!")
    else:
        print("  (none)")
    print()

    # Check if there are hash collisions in the database
    print("-" * 80)
    print("Checking for potential deduplication issues...")
    print("-" * 80)

    # Look for posts with attachments that have the same filename
    cursor.execute("""
        SELECT post_id, attachments
        FROM posts
        WHERE attachments IS NOT NULL
        AND jsonb_array_length(attachments) > 0
        AND creator_id = 'skyscript'
        ORDER BY post_id DESC
        LIMIT 50
    """)

    posts_with_same_filename = []
    for post_id, att_json in cursor.fetchall():
        if isinstance(att_json, str):
            atts = json.loads(att_json)
        else:
            atts = att_json

        for att in atts:
            if att.get('filename') == 'RG_EPM_1.pdf':
                posts_with_same_filename.append({
                    'post_id': post_id,
                    'url': att.get('url'),
                    'media_id': att.get('url', '').split('&m=')[1].split('&')[0] if '&m=' in att.get('url', '') else 'N/A'
                })

    if posts_with_same_filename:
        print(f"Found {len(posts_with_same_filename)} attachments with filename 'RG_EPM_1.pdf':")
        for item in posts_with_same_filename[:10]:
            print(f"  Post {item['post_id']}: media_id {item['media_id']}")
    else:
        print("No other posts with same filename found")

    conn.close()

if __name__ == '__main__':
    main()
