-- Initial schema for image processor
-- depends:

-- Images table - metadata for individual images including storage details

CREATE TABLE images (
  id SERIAL PRIMARY KEY,
  link TEXT NOT NULL,
  store_collection VARCHAR(256) NOT NULL,
  filepath TEXT NOT NULL,
  database_id VARCHAR(80),
  item_id BIGINT,
  property_name TEXT,
  image_number BIGINT,
  hashsum TEXT,
  extension VARCHAR(32) NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  stored_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Download attempts table - tracks history of failed and successful download attempts
CREATE TABLE failed_download_attempts (
  id SERIAL PRIMARY KEY,
  database_id VARCHAR(80),
  item_id BIGINT,
  property_name TEXT,
  image_number BIGINT,
  attempted_at TIMESTAMP DEFAULT NOW() NOT NULL,
  attempt_status VARCHAR(256),
  error_message TEXT,
  http_status INT,
  link TEXT NOT NULL,
  tries INT DEFAULT 1 NOT NULL
);

CREATE INDEX images_link_idx ON images (link);

-- uniaue store_collection and path
CREATE UNIQUE INDEX download_attempts_image_idx ON failed_download_attempts (database_id, item_id, property_name, image_number);

-- Constraint to ensure filepath is unique when present
ALTER TABLE images ADD CONSTRAINT filepath_unique UNIQUE (filepath, store_collection);

CREATE UNIQUE INDEX images_unique_link_idx ON images (database_id, item_id, property_name, image_number);

CREATE UNIQUE INDEX download_attempts_unique_link_idx ON failed_download_attempts (link);
