-- FIX: Move YouTube video AFTER the text that references it
-- Post 141632966: Swap order between video (pos 8) and reference text (pos 9)

BEGIN;

\echo '=== BEFORE: Current order ==='
SELECT
    (block->>'order')::int as order_num,
    block->>'type' as type,
    left(block->>'text', 60) as text_preview,
    CASE
        WHEN block->>'url' LIKE '%youtu%' THEN '🎥 VIDEO'
        WHEN block->>'text' LIKE '%3 min flash%' THEN '📝 REFERENCE TEXT'
        ELSE ''
    END as note
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND ((block->>'order')::int BETWEEN 8 AND 11)
ORDER BY (block->>'order')::int;

\echo ''
\echo '=== APPLYING FIX: Swapping orders ==='

-- Swap the order values:
-- - Video currently at order=9 → move to order=10
-- - Reference text currently at order=10 → move to order=9

UPDATE posts
SET content_blocks = (
    SELECT jsonb_agg(
        CASE
            -- Video: change order from 9 to 10
            WHEN (elem->>'order')::int = 9 AND elem->>'type' = 'video'
            THEN jsonb_set(elem, '{order}', '10')

            -- Reference text: change order from 10 to 9
            WHEN (elem->>'order')::int = 10 AND elem->>'text' LIKE '%3 min flash%'
            THEN jsonb_set(elem, '{order}', '9')

            -- Everything else: keep as-is
            ELSE elem
        END
        ORDER BY
            CASE
                WHEN (elem->>'order')::int = 9 AND elem->>'type' = 'video' THEN 10
                WHEN (elem->>'order')::int = 10 AND elem->>'text' LIKE '%3 min flash%' THEN 9
                ELSE (elem->>'order')::int
            END
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
        WHEN block->>'url' LIKE '%youtu%' THEN '✅ VIDEO (now after text)'
        WHEN block->>'text' LIKE '%3 min flash%' THEN '✅ REFERENCE TEXT (now before video)'
        ELSE ''
    END as note
FROM posts,
jsonb_array_elements(content_blocks::jsonb) AS block
WHERE post_id = '141632966'
AND ((block->>'order')::int BETWEEN 8 AND 11)
ORDER BY (block->>'order')::int;

\echo ''
\echo '=== VERIFICATION ==='
WITH video_order AS (
    SELECT (block->>'order')::int as ord
    FROM posts, jsonb_array_elements(content_blocks::jsonb) AS block
    WHERE post_id = '141632966' AND block->>'type' = 'video'
),
text_order AS (
    SELECT (block->>'order')::int as ord
    FROM posts, jsonb_array_elements(content_blocks::jsonb) AS block
    WHERE post_id = '141632966' AND block->>'text' LIKE '%3 min flash%'
)
SELECT
    CASE
        WHEN v.ord > t.ord THEN '✅ SUCCESS: Video is now AFTER reference text'
        ELSE '❌ FAILED: Something went wrong'
    END as result,
    'Text order: ' || t.ord || ', Video order: ' || v.ord as details
FROM video_order v, text_order t;

COMMIT;

\echo ''
\echo '✅ Changes committed. Video will now appear below the reference text.'
