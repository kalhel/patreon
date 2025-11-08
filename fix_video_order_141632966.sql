-- FIX: Move YouTube video AFTER the text that references it
-- Post 141632966: Change video order from 9 to 11 (after text at order 10)

BEGIN;

\echo '=== BEFORE: Current order ==='
SELECT
    (block->>'order')::int as order_num,
    block->>'type' as type,
    left(block->>'text', 60) as text_preview,
    CASE
        WHEN block->>'url' LIKE '%youtu%' THEN '🎥 VIDEO (order 9)'
        WHEN block->>'text' LIKE '%3 min flash%' THEN '📝 TEXT (order 10)'
        ELSE ''
    END as note
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND ((block->>'order')::int BETWEEN 8 AND 12)
ORDER BY (block->>'order')::int;

\echo ''
\echo '=== APPLYING FIX: Moving video from order 9 to 11 ==='

-- Simply change the video order from 9 to 11
UPDATE posts
SET content_blocks = (
    SELECT jsonb_agg(
        CASE
            -- Video: change order from 9 to 11
            WHEN (elem->>'order')::int = 9 AND elem->>'type' = 'video'
            THEN jsonb_set(elem, '{order}', '11')
            -- Everything else: keep as-is
            ELSE elem
        END
        ORDER BY (elem->>'order')::int
    )
    FROM jsonb_array_elements(content_blocks::jsonb) AS elem
)
WHERE post_id = '141632966';

\echo ''
\echo '=== AFTER: New order ==='
SELECT
    (block->>'order')::int as order_num,
    block->>'type' as type,
    left(block->>'text', 60) as text_preview,
    CASE
        WHEN block->>'url' LIKE '%youtu%' THEN '✅ VIDEO (now at order 11)'
        WHEN block->>'text' LIKE '%3 min flash%' THEN '✅ TEXT (order 10)'
        ELSE ''
    END as note
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND ((block->>'order')::int BETWEEN 8 AND 12)
ORDER BY (block->>'order')::int;

COMMIT;

\echo ''
\echo '✅ Changes committed. Video now appears after the reference text.'
