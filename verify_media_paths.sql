-- Verify media paths for debugging
-- Shows actual paths stored in database

-- Sample audio paths
SELECT
    post_id,
    title,
    audio_local_paths[1] as first_audio_path,
    array_length(audio_local_paths, 1) as audio_count
FROM posts
WHERE array_length(audio_local_paths, 1) > 0
AND deleted_at IS NULL
LIMIT 5;

-- Sample video paths
SELECT
    post_id,
    title,
    video_local_paths[1] as first_video_path,
    array_length(video_local_paths, 1) as video_count
FROM posts
WHERE array_length(video_local_paths, 1) > 0
AND deleted_at IS NULL
LIMIT 5;

-- Sample image paths
SELECT
    post_id,
    title,
    image_local_paths[1] as first_image_path,
    array_length(image_local_paths, 1) as image_count
FROM posts
WHERE array_length(image_local_paths, 1) > 0
AND deleted_at IS NULL
LIMIT 5;
