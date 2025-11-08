-- Reset all posts from astrobymax to pending status for re-processing
-- Change 'astrobymax' to any other creator_id as needed

-- Show what will be reset
SELECT COUNT(*) as total_posts
FROM posts
WHERE creator_id = 'astrobymax';

-- Reset all posts from creator
UPDATE posts
SET status = 'pending',
    details_extracted = false,
    attempt_count = 0
WHERE creator_id = 'astrobymax';

-- Verify the reset (show first 10)
SELECT post_id, title, status, details_extracted, attempt_count
FROM posts
WHERE creator_id = 'astrobymax'
ORDER BY post_id DESC
LIMIT 10;
