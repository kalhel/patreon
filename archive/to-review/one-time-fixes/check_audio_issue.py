#!/usr/bin/env python3
"""
Quick diagnostic to understand why audio filter is not working
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Try to use the same database connection as viewer
sys.path.insert(0, str(Path(__file__).parent.parent / 'web'))

try:
    from viewer import get_posts

    print("=" * 80)
    print("AUDIO FILTER DIAGNOSTIC")
    print("=" * 80)
    print()

    # Get all posts for astrobymax
    posts = get_posts(creator_id='astrobymax', source='sql')

    print(f"Total posts retrieved: {len(posts)}")
    print()

    # Check audio data
    posts_with_audio_paths = []
    posts_with_audios = []
    posts_with_audio_count = []

    for post in posts:
        audio_local = post.get('audio_local_paths')
        audios = post.get('audios')

        print(f"Post: {post.get('post_id')}")
        print(f"  audio_local_paths type: {type(audio_local)}, value: {audio_local}")
        print(f"  audios type: {type(audios)}, value: {audios}")

        # Check what the viewer logic would calculate
        audio_local_processed = audio_local or []
        if audio_local_processed:
            audio_count = len(audio_local_processed)
        else:
            audio_count = len(audios or [])

        print(f"  → Calculated audio_count: {audio_count}")
        print()

        if audio_local and len(audio_local) > 0:
            posts_with_audio_paths.append(post.get('post_id'))
        if audios and len(audios) > 0:
            posts_with_audios.append(post.get('post_id'))
        if audio_count > 0:
            posts_with_audio_count.append(post.get('post_id'))

        # Just check first 3 posts
        if len(posts_with_audio_paths) + len(posts_with_audios) >= 3:
            break

    print("=" * 80)
    print("SUMMARY:")
    print(f"  Posts with audio_local_paths: {len(posts_with_audio_paths)}")
    print(f"  Posts with audios: {len(posts_with_audios)}")
    print(f"  Posts that would show has_audio=True: {len(posts_with_audio_count)}")
    print("=" * 80)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
