-- Investigate post 141632966 video placement issue
\echo '=== POST 141632966 VIDEO INVESTIGATION ==='
\echo ''

-- Get basic post info
SELECT
    post_id,
    title,
    array_length(videos, 1) as video_count,
    videos
FROM posts
WHERE post_id = '141632966';

\echo ''
\echo '=== CONTENT BLOCKS ANALYSIS ==='
\echo ''

-- Get content blocks with order
SELECT
    jsonb_array_elements(content_blocks::jsonb) -> 'type' as block_type,
    jsonb_array_elements(content_blocks::jsonb) -> 'order' as block_order,
    jsonb_array_elements(content_blocks::jsonb) -> 'url' as url,
    left(jsonb_array_elements(content_blocks::jsonb) ->> 'text', 100) as text_preview
FROM posts
WHERE post_id = '141632966'
ORDER BY (jsonb_array_elements(content_blocks::jsonb) ->> 'order')::int;
