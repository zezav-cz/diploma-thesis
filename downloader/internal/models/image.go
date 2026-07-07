package models

import "time"

// ImageJob represents a job to download and process an image
type ImageJob struct {
	ImageURL     string `json:"image_url"`
	DatabaseID   string `json:"database_id"`
	ItemID       int    `json:"item_id"`
	PropertyName string `json:"property_name"`
	ImageNumber  *int   `json:"image_number"`
}

// ImageMetadata contains information about the image
type ImageMetadata struct {
	Width   int    `json:"width"`
	Height  int    `json:"height"`
	Type    string `json:"type"`    // jpeg, png, gif, webp, etc.
	HashSum string `json:"hashsum"` // SHA-256 hash of image data
}

// ProcessedImage contains the processed image with metadata
type ProcessedImage struct {
	ImageData []byte // Image in memory
	Metadata  ImageMetadata
	Job       ImageJob // Original job details
	StartedAt time.Time
}

// UploadRequest is the structure for HTTP upload
type UploadRequest struct {
	Metadata ImageMetadata `json:"metadata"`
}

// --- Database API Request/Response Models ---

type ImageCreate struct {
	Link string `json:"link"`

	StorageCollection string `json:"store_collection"`
	StoragePath       string `json:"filepath"`

	DatabaseID   string `json:"database_id"`
	ItemID       int    `json:"item_id"`
	PropertyName string `json:"property_name"`
	ImageNumber  *int   `json:"image_number,omitempty"`

	HashSum   string `json:"hashsum"`
	Extension string `json:"extension"`
	Width     int    `json:"width"`
	Height    int    `json:"height"`
}

// Image represents the response from creating an image record
type Image struct {
	ID int `json:"id"`

	Link string `json:"link"`

	StorageCollection string `json:"store_collection"`
	StoragePath       string `json:"filepath"`

	DatabaseID   string `json:"database_id"`
	ItemID       int    `json:"item_id"`
	PropertyName string `json:"property_name"`
	ImageNumber  *int   `json:"image_number,omitempty"`

	HashSum   string `json:"hashsum"`
	Extension string `json:"extension"`
	Width     int    `json:"width"`
	Height    int    `json:"height"`

	StoredAt time.Time `json:"stored_at"`
}

type AttemptedAttemptStatus string

const (
	AttemptStatusDownload AttemptedAttemptStatus = "download"
	AttemptStatusMetadata AttemptedAttemptStatus = "metadata"
	AttemptStatusUpload   AttemptedAttemptStatus = "upload"
)

// FailedDownloadRequest represents the request body for recording a failed download
type FailedDownloadAttempt struct {
	Link string `json:"link"`

	DatabaseID   string `json:"database_id"`
	ItemID       int    `json:"item_id"`
	PropertyName string `json:"property_name"`
	ImageNumber  *int   `json:"image_number,omitempty"`

	AttemptStatus *AttemptedAttemptStatus `json:"attempt_status,omitempty"`
	ErrorMessage  string                  `json:"error_message"`
	HttpStatus    int                     `json:"http_status"`
}

// UploadSuccessMessage represents a message published to Kafka when an image is successfully uploaded
type UploadSuccessMessage struct {
	DatabaseID        string `json:"database_id"`
	ItemID            int    `json:"item_id"`
	PropertyName      string `json:"property_name"`
	ImageNumber       *int   `json:"image_number,omitempty"`
	StorageCollection string `json:"storage_collection"`
	StoragePath       string `json:"storage_path"`
	OriginalURL       string `json:"original_url"`
	Width             int    `json:"width"`
	Height            int    `json:"height"`
	Extension         string `json:"extension"`
	HashSum           string `json:"hashsum"`
	UploadedAt        string `json:"uploaded_at"`
}
