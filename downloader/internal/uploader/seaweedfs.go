package uploader

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/models"
	"downloader/internal/producer"

	"github.com/linxGnu/goseaweedfs"
)

const (
	imageEndpointPath          = "/api/v1/images"
	failedDownloadEndpointPath = "/api/v1/failed-downloads-attempts/fail"
)

// SeaweedFSUploader handles uploading images to SeaweedFS and recording results to the database
type SeaweedFSUploader struct {
	// SeaweedFS client
	swfs *goseaweedfs.Seaweed

	// HTTP client for database API calls
	httpClient *http.Client

	// Database API base URL
	databaseAPIURL string

	// Kafka producer for success notifications
	kafkaProducer *producer.KafkaProducer

	// Configuration
	timeout time.Duration
}

// NewSeaweedFSUploader creates a new SeaweedFS uploader
func NewSeaweedFSUploader(cfg *config.Config, kafkaProducer *producer.KafkaProducer) (*SeaweedFSUploader, error) {
	// Initialize SeaweedFS client
	// Convert chunk size from MB to bytes
	chunkSizeBytes := int64(cfg.SeaweedFS.ChunkSizeMB) * 1024 * 1024

	swfs, err := goseaweedfs.NewSeaweed(
		cfg.SeaweedFS.MasterURL,
		[]string{cfg.SeaweedFS.FilerURL},
		chunkSizeBytes,
		&http.Client{
			Timeout: time.Duration(cfg.SeaweedFS.TimeoutSeconds) * time.Second,
		},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create SeaweedFS client: %w", err)
	}

	return &SeaweedFSUploader{
		swfs: swfs,
		httpClient: &http.Client{
			Timeout: time.Duration(cfg.SeaweedFS.TimeoutSeconds) * time.Second,
		},
		databaseAPIURL: cfg.DatabaseAPI.URL,
		kafkaProducer:  kafkaProducer,
		timeout:        time.Duration(cfg.SeaweedFS.TimeoutSeconds) * time.Second,
	}, nil
}

// Upload uploads an image to SeaweedFS and records it in the database
func (u *SeaweedFSUploader) Upload(ctx context.Context, processedImg *models.ProcessedImage) error {
	startTime := time.Now()

	const collectionName = "image_store"

	logger := logging.WithFields(map[string]interface{}{
		"database_id": processedImg.Job.DatabaseID,
		"item_id":     processedImg.Job.ItemID,
		"image_url":   processedImg.Job.ImageURL,
	})

	logger.Debug("Starting SeaweedFS upload")

	// 1. Upload to SeaweedFS
	// Generate filename from metadata
	fileName := u.generateFileName(processedImg)

	filePart, err := u.swfs.Filers()[0].Upload(
		bytes.NewReader(processedImg.ImageData),
		int64(len(processedImg.ImageData)),
		fileName,
		collectionName,
		"",
	)

	if err != nil {
		logger.WithError(err).Error("Failed to upload to SeaweedFS")
		// Record the failure in the database
		if recordErr := u.RecordFailure(ctx, processedImg.Job, fmt.Sprintf("SeaweedFS upload failed: %v", err), models.AttemptStatusUpload); recordErr != nil {
			logger.WithError(recordErr).Error("Failed to record upload failure")
		}
		return fmt.Errorf("seaweedfs upload failed: %w", err)
	}

	storagePath := u.generateStoragePath(processedImg, fileName)
	logger.WithFields(map[string]interface{}{
		"file_id":      filePart.FileID,
		"name":         filePart.Name,
		"storage_path": storagePath,
	}).Info("Uploaded to SeaweedFS")

	// 2. Record success in the database
	imageRecord := models.ImageCreate{
		Link: processedImg.Job.ImageURL,

		StorageCollection: collectionName,
		StoragePath:       storagePath,

		DatabaseID:   processedImg.Job.DatabaseID,
		ItemID:       processedImg.Job.ItemID,
		PropertyName: processedImg.Job.PropertyName,
		ImageNumber:  processedImg.Job.ImageNumber,

		HashSum:   processedImg.Metadata.HashSum,
		Extension: processedImg.Metadata.Type,
		Width:     processedImg.Metadata.Width,
		Height:    processedImg.Metadata.Height,
	}

	err = u.recordImageInDB(ctx, imageRecord)
	if err != nil {
		logger.WithError(err).Error("Failed to record image in database")
		// Image is uploaded to SeaweedFS but not in DB - this is a critical issue
		// You might want to implement cleanup or retry logic here
		return fmt.Errorf("failed to record image in database: %w", err)
	}

	// 3. Publish success message to Kafka
	successMsg := &models.UploadSuccessMessage{
		DatabaseID:        processedImg.Job.DatabaseID,
		ItemID:            processedImg.Job.ItemID,
		PropertyName:      processedImg.Job.PropertyName,
		ImageNumber:       processedImg.Job.ImageNumber,
		StorageCollection: collectionName,
		StoragePath:       storagePath,
		OriginalURL:       processedImg.Job.ImageURL,
		Width:             processedImg.Metadata.Width,
		Height:            processedImg.Metadata.Height,
		Extension:         processedImg.Metadata.Type,
		HashSum:           processedImg.Metadata.HashSum,
		UploadedAt:        time.Now().UTC().Format(time.RFC3339),
	}

	if err := u.kafkaProducer.PublishUploadSuccess(ctx, successMsg); err != nil {
		logger.WithError(err).Error("Failed to publish upload success message to Kafka")
		// Don't return error here as the upload was successful
		// The Kafka message is a notification, not a critical path
	}

	logger.WithField("duration_ms", time.Since(startTime).Milliseconds()).
		WithField("total_duration_ms", time.Since(processedImg.StartedAt).Milliseconds()).
		Info("Image uploaded and recorded successfully")

	return nil
}

// RecordFailure records a failed download/upload attempt in the database
func (u *SeaweedFSUploader) RecordFailure(ctx context.Context, job models.ImageJob, reason string, status models.AttemptedAttemptStatus) error {
	logger := logging.WithFields(map[string]interface{}{
		"database_id": job.DatabaseID,
		"item_id":     job.ItemID,
		"image_url":   job.ImageURL,
	})

	logger.Info("Making REAL API call to record failed download attempt")

	failureRequest := models.FailedDownloadAttempt{
		Link: job.ImageURL,

		DatabaseID:   job.DatabaseID,
		ItemID:       job.ItemID,
		PropertyName: job.PropertyName,
		ImageNumber:  job.ImageNumber,

		AttemptStatus: &status,
		ErrorMessage:  reason,
		HttpStatus:    101,
	}

	payload, err := json.Marshal(failureRequest)
	if err != nil {
		return fmt.Errorf("failed to marshal failure request: %w", err)
	}

	url := u.databaseAPIURL + failedDownloadEndpointPath
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("failed to create failure record request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := u.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to record failure: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status code when recording failure: %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	logger.Info("Failed download attempt recorded successfully")
	return nil
}

// recordImageInDB records the image metadata in the database
func (u *SeaweedFSUploader) recordImageInDB(ctx context.Context, imageRecord models.ImageCreate) error {
	payload, err := json.Marshal(imageRecord)
	if err != nil {
		return fmt.Errorf("failed to marshal image record: %w", err)
	}

	url := u.databaseAPIURL + imageEndpointPath
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("failed to create image record request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := u.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to record image: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status code when recording image: %d, body: %s", resp.StatusCode, string(bodyBytes))
	}

	return nil
}

// generateFileName generates a filename for the image
// Format: {property_name}_{image_number}.{format}
func (u *SeaweedFSUploader) generateFileName(processedImg *models.ProcessedImage) string {
	imageNumStr := ""
	if processedImg.Job.ImageNumber != nil {
		imageNumStr = fmt.Sprintf("_%d", *processedImg.Job.ImageNumber)
	}

	return fmt.Sprintf("images/%s/%s_%d%s.%s",
		processedImg.Job.DatabaseID,
		processedImg.Job.PropertyName,
		processedImg.Job.ItemID,
		imageNumStr,
		processedImg.Metadata.Type,
	)
}

// generateStoragePath generates a storage path identifier
// Format: seaweedfs://{fid} or a custom format for your database
func (u *SeaweedFSUploader) generateStoragePath(processedImg *models.ProcessedImage, fid string) string {
	// Store the SeaweedFS file ID as the storage path
	// You can also use a custom format like: /images/{database_id}/{item_id}/{fid}
	return fmt.Sprintf("seaweedfs://%s", fid)
}

// Close closes the uploader and its resources
func (u *SeaweedFSUploader) Close() {
	if u.kafkaProducer != nil {
		u.kafkaProducer.Close()
	}
}
