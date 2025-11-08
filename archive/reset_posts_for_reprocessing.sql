-- Reset specific posts to pending status for re-processing with fixed scraper
-- These posts had issues with images not appearing or appearing multiple times

UPDATE posts
SET status = 'pending',
    details_extracted = false,
    attempt_count = 0
WHERE post_id IN ('111538285', '141080275', '113258529');

-- Verify the reset
SELECT post_id, title, status, details_extracted, attempt_count
FROM posts
WHERE post_id IN ('111538285', '141080275', '113258529');
