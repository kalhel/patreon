#!/usr/bin/env python3
"""
Debug script to investigate attachment count discrepancy for post 139945403
- Index shows: 2 attachments
- Post.html shows: 1 attachment
"""

import psycopg2
import json
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    print("=" * 80)
    print("DEBUG: Post 139945403 Attachment Investigation")
    print("=" * 80)
    print()

    # Connect to PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'alejandria'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        print("✓ Connected to PostgreSQL")
        print()
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return

    cursor = conn.cursor()

    # Query post data
    cursor.execute("""
        SELECT post_id, title, attachments, attachment_local_paths, content_blocks
        FROM posts
        WHERE post_id = '139945403'
    """)

    row = cursor.fetchone()

    if not row:
        print("✗ Post not found in database")
        conn.close()
        return

    post_id, title, attachments_json, attachment_local_json, content_blocks_json = row

    print(f"Post ID: {post_id}")
    print(f"Title: {title}")
    print()

    # Parse JSON fields (PostgreSQL may return as dict/list or as string)
    if isinstance(attachments_json, str):
        attachments = json.loads(attachments_json) if attachments_json else []
    else:
        attachments = attachments_json if attachments_json else []

    if isinstance(attachment_local_json, str):
        attachment_local = json.loads(attachment_local_json) if attachment_local_json else []
    else:
        attachment_local = attachment_local_json if attachment_local_json else []

    if isinstance(content_blocks_json, str):
        content_blocks = json.loads(content_blocks_json) if content_blocks_json else []
    else:
        content_blocks = content_blocks_json if content_blocks_json else []

    print("-" * 80)
    print("1. SQL FIELDS (raw data)")
    print("-" * 80)
    print(f"attachments field: {len(attachments)} items")
    if attachments:
        for i, att in enumerate(attachments, 1):
            if isinstance(att, dict):
                print(f"  {i}. filename: {att.get('filename', 'N/A')}")
                print(f"      url: {att.get('url', 'N/A')[:80]}...")
            else:
                print(f"  {i}. {att}")
    else:
        print("  (empty)")
    print()

    print(f"attachment_local_paths field: {len(attachment_local)} items")
    if attachment_local:
        for i, path in enumerate(attachment_local, 1):
            print(f"  {i}. {path}")
    else:
        print("  (empty)")
    print()

    # Analyze content_blocks for link-type attachments
    link_blocks = [b for b in content_blocks if b.get('type') == 'link' and 'patreon.com/file' in b.get('url', '')]

    print("-" * 80)
    print("2. CONTENT BLOCKS (link blocks with file URLs)")
    print("-" * 80)
    print(f"Link blocks with 'patreon.com/file': {len(link_blocks)}")

    unique_media_ids = {}
    if link_blocks:
        for i, block in enumerate(link_blocks, 1):
            url = block.get('url', '')
            text = block.get('text', 'N/A')
            order = block.get('order', 'N/A')

            # Extract media ID
            media_id = 'N/A'
            if '&m=' in url:
                media_id = url.split('&m=')[1].split('&')[0]
                if media_id not in unique_media_ids:
                    unique_media_ids[media_id] = []
                unique_media_ids[media_id].append(order)

            print(f"  {i}. {text} (order: {order}, media_id: {media_id})")

        print()
        print(f"Unique media IDs: {len(unique_media_ids)}")
        for media_id, orders in unique_media_ids.items():
            print(f"  - {media_id}: appears {len(orders)} times (orders: {orders})")
    else:
        print("  (none found)")
    print()

    # Show how templates count attachments
    print("-" * 80)
    print("3. HOW TEMPLATES COUNT")
    print("-" * 80)

    # Index.html counting logic
    print("Index.html (line 1546):")
    print("  att_count = post.attachments | length")
    print(f"  Result: {len(attachments)}")
    print()

    # Post.html/viewer.py counting logic
    print("Post.html/viewer.py (line 560):")
    print("  attachment_count = len(attachment_local) if attachment_local else len(attachments)")
    result = len(attachment_local) if attachment_local else len(attachments)
    print(f"  Result: {result}")
    print()

    # Summary
    print("-" * 80)
    print("4. SUMMARY")
    print("-" * 80)
    print(f"SQL attachments field:         {len(attachments)} items")
    print(f"SQL attachment_local_paths:    {len(attachment_local)} items")
    print(f"Link blocks in content_blocks: {len(link_blocks)} items")
    print(f"Unique media IDs:              {len(unique_media_ids)} items")
    print()
    print("Expected counts:")
    print(f"  Index should show:  {len(attachments)}")
    print(f"  Post should show:   {result}")
    print()
    print("Actual counts (reported by user):")
    print("  Index shows:  2")
    print("  Post shows:   1")
    print()

    if len(attachments) != 2:
        print("⚠️  MISMATCH: SQL attachments field doesn't have 2 items!")
        print("   Possible causes:")
        print("   - Scraper only captured 1 attachment during phase2")
        print("   - Data was modified after scraping")
        print("   - User is looking at different data source")

    if result != 1:
        print("⚠️  MISMATCH: post.html calculation doesn't result in 1!")
        print("   Template counting logic may be correct")

    conn.close()

if __name__ == '__main__':
    main()
