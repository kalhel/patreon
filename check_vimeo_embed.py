#!/usr/bin/env python3
"""
Check content_blocks for Vimeo embed in post 141632966
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT')
)

cursor = conn.cursor()
cursor.execute("SELECT content_blocks FROM posts WHERE post_id = '141632966'")
row = cursor.fetchone()

if row:
    content_blocks = row[0]

    print(f'Total content blocks: {len(content_blocks)}')
    print()

    # Find video/iframe blocks
    video_blocks = [b for b in content_blocks if b.get('type') in ('video', 'vimeo_embed', 'iframe', 'youtube_embed')]

    print(f'Video-related blocks: {len(video_blocks)}')
    for i, block in enumerate(video_blocks, 1):
        print(f'\n{i}. Type: {block.get("type")}')
        print(f'   URL: {block.get("url", "N/A")}')
        print(f'   Order: {block.get("order", "N/A")}')

    if not video_blocks:
        print('\n⚠️  No video/iframe blocks found!')
        print('\nShowing all block types:')
        from collections import Counter
        types = [b.get('type') for b in content_blocks]
        for block_type, count in Counter(types).most_common():
            print(f'  {block_type}: {count}')
else:
    print('Post not found')

conn.close()
