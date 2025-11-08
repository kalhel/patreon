-- Check which collections are missing images
SELECT
    creator_id,
    COUNT(*) as collections_count,
    COUNT(collection_image) as with_remote_image,
    COUNT(collection_image_local) as with_local_image
FROM collections
WHERE deleted_at IS NULL
GROUP BY creator_id
ORDER BY collections_count DESC;

-- Show collections without images
SELECT
    collection_id,
    creator_id,
    title,
    post_count,
    collection_url
FROM collections
WHERE deleted_at IS NULL
AND (collection_image IS NULL OR collection_image_local IS NULL)
ORDER BY creator_id, collection_id;
