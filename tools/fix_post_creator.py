#!/usr/bin/env python3
"""
Fix creator_id for post 128693945 in PostgreSQL
Changes creator_id from 'astrobymax' to 'headonhistory'
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from postgres_tracker import PostgresTracker

def main():
    print("🔥 Fixing creator_id for post 128693945...")
    print()

    # Initialize PostgreSQL tracker
    try:
        tracker = PostgresTracker()
    except Exception as e:
        print(f"❌ Error initializing PostgreSQL tracker: {e}")
        print("   Make sure .env file exists and is configured.")
        return 1

    # Get the post
    post_id = '128693945'
    post = tracker.get_post(post_id)

    if not post:
        print(f"❌ Post {post_id} not found in database")
        return 1

    # Show current state
    current_creator = post.get('creator_id', 'unknown')
    print(f"📊 Current state:")
    print(f"   Post ID: {post_id}")
    print(f"   Current creator_id: {current_creator}")

    # Check post_metadata for correct creator
    if 'post_metadata' in post:
        metadata_creator = post.get('post_metadata', {}).get('creator_name', 'N/A')
        print(f"   Metadata creator_name: {metadata_creator}")

    print()

    # Confirm change
    if current_creator == 'headonhistory':
        print(f"✅ Post {post_id} already has correct creator_id: headonhistory")
        return 0

    # Update creator_id
    print(f"🔧 Updating creator_id from '{current_creator}' to 'headonhistory'...")

    success = tracker._patch(f"posts/{post_id}", {
        "creator_id": "headonhistory",
        "updated_at": post.get('updated_at', '')  # Keep original updated_at or set current
    })

    if success:
        print(f"✅ Successfully updated post {post_id}")
        print(f"   New creator_id: headonhistory")
        print()

        # Verify
        updated_post = tracker.get_post(post_id)
        if updated_post and updated_post.get('creator_id') == 'headonhistory':
            print("✅ Verification successful - creator_id updated correctly")
        else:
            print("⚠️  Warning: Could not verify update")
    else:
        print(f"❌ Failed to update post {post_id}")
        return 1

    print()
    print("🎉 Done! The post should now appear correctly filtered in the web viewer.")
    print("   Reload the Flask web app to see the changes.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
