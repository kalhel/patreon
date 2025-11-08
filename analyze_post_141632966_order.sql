-- Analyze content block order for post 141632966
-- Find where YouTube video is placed and where it should be

\echo '=== CONTENT BLOCKS IN ORDER ==='
\echo ''

WITH blocks AS (
    SELECT
        post_id,
        ordinality as position,
        block ->> 'type' as type,
        (block ->> 'order')::int as original_order,
        block ->> 'url' as url,
        left(block ->> 'text', 150) as text_preview,
        block ->> 'local_path' as local_path
    FROM posts,
    jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966'
)
SELECT
    position,
    original_order,
    type,
    CASE
        WHEN url LIKE '%youtu%' THEN '🎥 YOUTUBE'
        WHEN url LIKE '%vimeo%' THEN '🎥 VIMEO'
        WHEN url LIKE '%mux%' THEN '🎥 MUX'
        ELSE ''
    END as video_type,
    CASE
        WHEN text_preview LIKE '%3 min flash%' THEN '⭐ REFERENCE TEXT'
        ELSE ''
    END as note,
    text_preview,
    url,
    local_path
FROM blocks
ORDER BY position;

\echo ''
\echo '=== DIAGNOSIS ==='
\echo ''

SELECT
    'YouTube video is at position ' || position || ' (order: ' || original_order || ')' as finding
FROM (
    SELECT
        ordinality as position,
        (block ->> 'order')::int as original_order
    FROM posts,
    jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966'
    AND block ->> 'url' LIKE '%youtu%'
) youtube

UNION ALL

SELECT
    'Reference text "3 min flash" is at position ' || position || ' (order: ' || original_order || ')'
FROM (
    SELECT
        ordinality as position,
        (block ->> 'order')::int as original_order
    FROM posts,
    jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966'
    AND block ->> 'text' LIKE '%3 min flash%'
) reference_text

UNION ALL

SELECT
    'Found Vimeo URL: ' || block ->> 'url'
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND block ->> 'url' LIKE '%vimeo%'

UNION ALL

SELECT
    'Vimeo embed in HTML text: ' || substring(block ->> 'text' FROM 'vimeo[^"<>]*')
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND block ->> 'text' LIKE '%vimeo%';
