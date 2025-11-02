#!/usr/bin/env python3
"""Test script to verify IMAGE + DURATION + AUDIO merging logic"""

import sys
import re
sys.path.insert(0, 'src')

# Create test blocks simulating what we extract from Patreon
test_blocks = [
    {
        'type': 'image',
        'order': 1,
        'url': 'https://example.com/audio-thumbnail.jpg'
    },
    {
        'type': 'paragraph',
        'order': 2,
        'text': '36:40'
    },
    {
        'type': 'audio',
        'order': 3,
        'url': 'https://example.com/audio.mp3'
    }
]

print("=" * 60)
print("TEST: IMAGE + DURATION + AUDIO merging")
print("=" * 60)

print("\nInput blocks:")
for i, block in enumerate(test_blocks, 1):
    print(f"{i}. {block['type'].upper()}", end="")
    if block['type'] == 'paragraph':
        print(f" - Text: {block.get('text', '')}")
    elif block['type'] in ['image', 'audio']:
        print(f" - URL: {block.get('url', '')[:50]}...")
    else:
        print()

# Simulate the post-processing logic
import re
final_cleaned = []
i = 0

while i < len(test_blocks):
    block = test_blocks[i]

    # Check for IMAGE + DURATION + AUDIO pattern (most specific, check first)
    if block['type'] == 'image' and i + 2 < len(test_blocks):
        potential_duration = test_blocks[i + 1]
        potential_audio = test_blocks[i + 2]

        if potential_duration['type'] == 'paragraph' and potential_audio['type'] == 'audio':
            duration_text = potential_duration.get('text', '').strip()
            # Match duration format: 36:40, 1:23:45, etc.
            if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', duration_text):
                # This is the pattern! Merge all three
                potential_audio['thumbnail'] = block.get('url')
                potential_audio['duration'] = duration_text
                final_cleaned.append(potential_audio)
                i += 3
                continue

    # Check for IMAGE + AUDIO pattern (no duration paragraph between them)
    if block['type'] == 'image' and i + 1 < len(test_blocks):
        next_block = test_blocks[i + 1]
        if next_block['type'] == 'audio':
            # Associate image as thumbnail
            next_block['thumbnail'] = block.get('url')
            # Skip image, add audio
            i += 2
            final_cleaned.append(next_block)
            continue

    # Check for DURATION + AUDIO pattern (might have IMAGE before in final_cleaned)
    if block['type'] == 'paragraph' and i + 1 < len(test_blocks):
        text = block.get('text', '').strip()
        next_block = test_blocks[i + 1]
        # Match duration format: 36:40, 1:23:45, etc.
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', text) and next_block['type'] == 'audio':
            # Check if the previous block in final_cleaned is an image
            # If so, pop it and associate it with this audio
            if final_cleaned and final_cleaned[-1]['type'] == 'image':
                last_image = final_cleaned.pop()  # Remove the image we just added
                next_block['thumbnail'] = last_image.get('url')
                next_block['duration'] = text
                final_cleaned.append(next_block)
                i += 2
                continue
            else:
                # No image before, just merge duration with audio
                next_block['duration'] = text
                final_cleaned.append(next_block)
                i += 2
                continue

    # Default: add block as-is
    final_cleaned.append(block)
    i += 1

print("\nOutput blocks after post-processing:")
for i, block in enumerate(final_cleaned, 1):
    print(f"{i}. {block['type'].upper()}")
    if block['type'] == 'audio':
        print(f"   - URL: {block.get('url', '')[:50]}...")
        print(f"   - Thumbnail: {block.get('thumbnail', 'NO')[:50] if block.get('thumbnail') else 'NO'}")
        print(f"   - Duration: {block.get('duration', 'NO')}")

print("\n" + "=" * 60)
if len(final_cleaned) == 1 and final_cleaned[0]['type'] == 'audio':
    audio = final_cleaned[0]
    if audio.get('thumbnail') and audio.get('duration') == '36:40':
        print("✅ TEST PASSED: Audio block has thumbnail and duration!")
    else:
        print("❌ TEST FAILED: Audio block missing thumbnail or duration")
        print(f"   Thumbnail: {audio.get('thumbnail', 'MISSING')}")
        print(f"   Duration: {audio.get('duration', 'MISSING')}")
else:
    print(f"❌ TEST FAILED: Expected 1 audio block, got {len(final_cleaned)} blocks")
print("=" * 60)
