-- Check if collections have images after scraping
SELECT
    creator_id,
    collection_id,
    title,
    post_count,
    CASE
        WHEN collection_image IS NOT NULL THEN '✅ Yes'
        ELSE '❌ No'
    END as has_remote_image,
    CASE
        WHEN collection_image_local IS NOT NULL THEN '✅ Yes'
        ELSE '❌ No'
    END as has_local_image,
    collection_image_local
FROM collections
WHERE creator_id IN ('astrobymax', 'horoiproject', 'skyscript')
AND deleted_at IS NULL
ORDER BY creator_id, collection_id;

-- Count by creator
SELECT
    creator_id,
    COUNT(*) as total,
    COUNT(collection_image) as with_remote,
    COUNT(collection_image_local) as with_local
FROM collections
WHERE creator_id IN ('astrobymax', 'horoiproject', 'skyscript')
AND deleted_at IS NULL
GROUP BY creator_id;
