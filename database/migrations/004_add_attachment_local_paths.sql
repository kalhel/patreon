-- ============================================================================
-- Migration: Add attachment_local_paths column for downloaded attachments
-- Date: 2025-11-08
-- ============================================================================

-- Add column for storing paths to downloaded attachment files
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS attachment_local_paths TEXT[];

-- Create index for querying posts with downloaded attachments
CREATE INDEX IF NOT EXISTS idx_posts_attachment_local_paths
ON posts USING GIN(attachment_local_paths);

-- Add comment for documentation
COMMENT ON COLUMN posts.attachment_local_paths IS
'Relative paths to downloaded attachment files (PDFs, documents, etc.)
from data/media/ directory. Example: ["attachments/astrobymax/document.pdf"]';
