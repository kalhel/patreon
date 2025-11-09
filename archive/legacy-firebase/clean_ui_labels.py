#!/usr/bin/env python3
"""Clean UI labels from already scraped posts"""

import json

# UI labels to filter out
ui_labels = ['author', 'tags', 'home', 'posts', 'share', 'like', 'comment']

# Load the data
with open('data/processed/headonhistory_posts_detailed.json', 'r') as f:
    posts = json.load(f)

cleaned_count = 0
for post in posts:
    blocks = post.get('content_blocks', [])
    original_count = len(blocks)

    # Filter out UI label paragraphs
    cleaned_blocks = []
    for block in blocks:
        text = block.get('text', '').lower().strip()
        # Skip if it's a text/paragraph block with a UI label
        if block['type'] in ['text', 'paragraph'] and text in ui_labels:
            cleaned_count += 1
            print(f"Removed '{text}' from post {post['post_id']} (block {block['order']})")
            continue
        cleaned_blocks.append(block)

    # Re-order blocks
    for i, block in enumerate(cleaned_blocks, 1):
        block['order'] = i

    post['content_blocks'] = cleaned_blocks

    if len(cleaned_blocks) != original_count:
        print(f"  Post {post['post_id']}: {original_count} → {len(cleaned_blocks)} blocks")

# Save cleaned data
with open('data/processed/headonhistory_posts_detailed.json', 'w') as f:
    json.dump(posts, f, indent=2, ensure_ascii=False)

print(f"\nCleaned {cleaned_count} UI label blocks")
