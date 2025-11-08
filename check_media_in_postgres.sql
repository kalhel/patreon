-- Check media in PostgreSQL posts
-- This helps diagnose if videos/audios are stored correctly

-- 1. Count posts with media
SELECT
    'Posts with images' as type,
    COUNT(*) as count
FROM posts
WHERE array_length(image_local_paths, 1) > 0
AND deleted_at IS NULL

UNION ALL

SELECT
    'Posts with videos' as type,
    COUNT(*) as count
FROM posts
WHERE array_length(video_local_paths, 1) > 0
AND deleted_at IS NULL

UNION ALL

SELECT
    'Posts with audios' as type,
    COUNT(*) as count
FROM posts
WHERE array_length(audio_local_paths, 1) > 0
AND deleted_at IS NULL;

-- 2. Show sample post with videos
SELECT
    post_id,
    creator_id,
    title,
    array_length(video_local_paths, 1) as video_count,
    video_local_paths[1] as first_video_path,
    array_length(video_streams, 1) as streams_count
FROM posts
WHERE array_length(video_local_paths, 1) > 0
AND deleted_at IS NULL
LIMIT 5;

-- 3. Show sample post with audios
SELECT
    post_id,
    creator_id,
    title,
    array_length(audio_local_paths, 1) as audio_count,
    audio_local_paths[1] as first_audio_path
FROM posts
WHERE array_length(audio_local_paths, 1) > 0
AND deleted_at IS NULL
LIMIT 5;

-- 4. Check content_blocks for media
SELECT
    post_id,
    title,
    jsonb_array_length(content_blocks) as total_blocks,
    (
        SELECT COUNT(*)
        FROM jsonb_array_elements(content_blocks) AS block
        WHERE block->>'type' = 'video'
    ) as video_blocks,
    (
        SELECT COUNT(*)
        FROM jsonb_array_elements(content_blocks) AS block
        WHERE block->>'type' = 'audio'
    ) as audio_blocks
FROM posts
WHERE content_blocks IS NOT NULL
AND jsonb_array_length(content_blocks) > 0
AND deleted_at IS NULL
LIMIT 10;
