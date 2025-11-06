#!/usr/bin/env python3
"""Reset processed posts in Firebase to pending state"""

import sys
sys.path.insert(0, 'src')

from firebase_tracker import load_firebase_config, FirebaseTracker

database_url, database_secret = load_firebase_config()
tracker = FirebaseTracker(database_url, database_secret)

# Get all posts
all_posts = tracker.get_all_posts()

# Find posts that are marked as details_extracted
processed_posts = []
for post_id, post in all_posts.items():
    if post.get('status', {}).get('details_extracted', False):
        processed_posts.append(post_id)

print(f"Found {len(processed_posts)} posts marked as processed:")
for post_id in processed_posts:
    print(f"  - {post_id}")

# Reset them to pending
print("\nResetting to pending state...")
for post_id in processed_posts:
    tracker.mark_details_extracted(post_id, success=False, error=None)
    print(f"  ✓ Reset {post_id}")

print(f"\n✅ Reset {len(processed_posts)} posts to pending state")

# Update creator stats
tracker.update_creator_stats('headonhistory')
tracker.update_creator_stats('astrobymax')
tracker.update_creator_stats('horoiproject')

# Show new summary
tracker.print_summary()
