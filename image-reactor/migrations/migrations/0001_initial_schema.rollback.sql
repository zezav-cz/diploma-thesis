-- Rollback initial schema
-- depends:

DROP INDEX IF EXISTS images_unique_link_idx;
DROP INDEX IF EXISTS download_attempts_image_idx;
DROP TABLE IF EXISTS download_attempts;
DROP TABLE IF EXISTS images;
