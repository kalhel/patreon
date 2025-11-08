-- FIX: Reorder content blocks for post 141632966
-- Move YouTube video (position 8, order 9) to after reference text (position 9, order 10)
-- SAFE: Creates backup before making changes

\echo '=== FIXING POST 141632966 CONTENT BLOCK ORDER ==='
\echo ''

BEGIN;

\echo 'Step 1: Show current problematic order'
\echo '---------------------------------------'
WITH blocks AS (
    SELECT
        ordinality - 1 as position,
        (block->>'order')::int as order_num,
        block->>'type' as type,
        left(block->>'text', 80) as text_preview,
        block->>'url' as url
    FROM posts,
    jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966'
)
SELECT position, order_num, type,
    CASE
        WHEN position = 8 THEN '← VIDEO (needs to move DOWN)'
        WHEN position = 9 THEN '← TEXT (video should be AFTER this)'
        ELSE ''
    END as note,
    text_preview
FROM blocks
WHERE position IN (7, 8, 9, 10)
ORDER BY position;

\echo ''
\echo 'Step 2: Create backup (just in case)'
\echo '------------------------------------'
CREATE TEMP TABLE post_141632966_backup AS
SELECT * FROM posts WHERE post_id = '141632966';

SELECT 'Backup created: ' || count(*) || ' row(s)' as backup_status
FROM post_141632966_backup;

\echo ''
\echo 'Step 3: Apply fix - swap order numbers'
\echo '--------------------------------------'
-- Strategy: Swap the order values between position 8 (YouTube video) and position 9 (reference text)
-- This will cause them to render in the correct order

UPDATE posts
SET content_blocks = (
    SELECT jsonb_agg(
        CASE
            -- Position 8 (YouTube video): change order from 9 to 10
            WHEN (elem->>'order')::int = 9 AND elem->>'type' = 'video' AND elem->>'url' LIKE '%youtu%'
            THEN jsonb_set(elem, '{order}', '10')

            -- Position 9 (reference text): change order from 10 to 9
            WHEN (elem->>'order')::int = 10 AND elem->>'text' LIKE '%3 min flash%'
            THEN jsonb_set(elem, '{order}', '9')

            -- All other blocks: keep as-is
            ELSE elem
        END
        ORDER BY (elem->>'order')::int
    )
    FROM jsonb_array_elements(content_blocks::jsonb) AS elem
)
WHERE post_id = '141632966';

SELECT 'Updated ' || count(*) || ' post(s)' as update_status
FROM posts WHERE post_id = '141632966';

\echo ''
\echo 'Step 4: Verify the fix'
\echo '----------------------'
WITH blocks AS (
    SELECT
        ordinality - 1 as position,
        (block->>'order')::int as order_num,
        block->>'type' as type,
        left(block->>'text', 80) as text_preview
    FROM posts,
    jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966'
)
SELECT position, order_num, type,
    CASE
        WHEN type = 'video' AND position = 9 THEN '✓ VIDEO NOW IN CORRECT POSITION'
        WHEN text_preview LIKE '%3 min flash%' AND position = 8 THEN '✓ TEXT NOW BEFORE VIDEO'
        ELSE ''
    END as note,
    text_preview
FROM blocks
WHERE position IN (7, 8, 9, 10)
ORDER BY position;

\echo ''
\echo '=== VERIFICATION ==='
\echo ''

-- Final check: video should now be AFTER the reference text
WITH video_pos AS (
    SELECT ordinality - 1 as pos
    FROM posts, jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966' AND block->>'url' LIKE '%youtu%'
),
text_pos AS (
    SELECT ordinality - 1 as pos
    FROM posts, jsonb_array_elements(content_blocks::jsonb) WITH ORDINALITY AS block
    WHERE post_id = '141632966' AND block->>'text' LIKE '%3 min flash%'
)
SELECT
    CASE
        WHEN v.pos > t.pos THEN '✓✓✓ SUCCESS: Video is now positioned AFTER the reference text'
        WHEN v.pos < t.pos THEN '✗✗✗ FAILED: Video is still BEFORE the reference text'
        ELSE '? UNKNOWN: Could not determine positions'
    END as result,
    'Text at position ' || t.pos || ', Video at position ' || v.pos as details
FROM video_pos v, text_pos t;

\echo ''
\echo '=== READY TO COMMIT ==='
\echo ''
\echo 'Review the verification above.'
\echo 'If everything looks correct, type: COMMIT;'
\echo 'If something is wrong, type: ROLLBACK;'
\echo ''

-- Don't auto-commit - let user review and decide
-- COMMIT;
