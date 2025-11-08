-- =====================================================
-- Add image columns to collections table
-- =====================================================

-- Add collection_image column (remote URL)
ALTER TABLE collections
ADD COLUMN IF NOT EXISTS collection_image TEXT;

-- Add collection_image_local column (local path)
ALTER TABLE collections
ADD COLUMN IF NOT EXISTS collection_image_local TEXT;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_collections_image_local ON collections(collection_image_local);

-- Verify columns were added
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'collections'
AND column_name IN ('collection_image', 'collection_image_local');

-- Show current state
SELECT
    COUNT(*) as total_collections,
    COUNT(collection_image) as with_remote_image,
    COUNT(collection_image_local) as with_local_image
FROM collections
WHERE deleted_at IS NULL;
