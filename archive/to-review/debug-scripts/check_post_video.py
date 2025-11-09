#!/usr/bin/env python3
"""
Quick check: What's in the videos field for post 96242312?
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'alejandria'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)

cursor = conn.cursor()
cursor.execute("SELECT post_id, videos FROM posts WHERE post_id = '96242312'")
row = cursor.fetchone()

if row:
    post_id, videos = row
    print(f"Post {post_id}")
    print(f"Type of videos field: {type(videos)}")
    print(f"Videos value: {videos}")
    print(f"Length: {len(videos) if videos else 0}")

    if videos:
        print("\nVideos:")
        for i, v in enumerate(videos, 1):
            print(f"  {i}. {v}")
            print(f"     Has 'stream.mux.com': {'stream.mux.com' in v.lower()}")
            print(f"     Has 'time=': {'time=' in v.lower()}")
else:
    print("Post not found")

conn.close()
