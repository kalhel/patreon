-- Fix creator_id mismatches for posts appearing incorrectly in filters
-- Issue: Posts from headonhistory and horoiproject were showing in astrobymax filter

-- Post 96097452 & 77933294: "The Almanac of 2024/2023" by Ali A Olomi
UPDATE posts SET creator_id = 'headonhistory' WHERE post_id = '96097452';
UPDATE posts SET creator_id = 'headonhistory' WHERE post_id = '77933294';

-- Post 42294201: "Abū Saʿīd Shādhān..." by HOROI Project
UPDATE posts SET creator_id = 'horoiproject' WHERE post_id = '42294201';

-- Verify the fix
SELECT post_id, creator_id, creator_name, title
FROM posts
WHERE post_id IN ('96097452', '77933294', '42294201');
