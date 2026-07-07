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
)

const (
	mockImageEndpointPath          = "/api/v1/images"
	mockFailedDownloadEndpointPath = "/api/v1/failed-downloads-attempts/fail"
)

// MockSeaweedFSUploader is a mock uploader that simulates SeaweedFS uploads without actually uploading
// It only makes database API calls, useful for testing the API integration
type MockSeaweedFSUploader struct {
	// HTTP client for database API calls
	httpClient *http.Client

	// Database API base URL
	databaseAPIURL string

	// Kafka producer for success notifications
	kafkaProducer *producer.KafkaProducer

	// Configuration
	timeout       time.Duration
	mockSleepTime time.Duration
}

// NewMockSeaweedFSUploader creates a new mock SeaweedFS uploader
func NewMockSeaweedFSUploader(cfg *config.Config, kafkaProducer *producer.KafkaProducer) (*MockSeaweedFSUploader, error) {
	return &MockSeaweedFSUploader{
		httpClient: &http.Client{
			Timeout: time.Duration(cfg.SeaweedFS.TimeoutSeconds) * time.Second,
		},
		databaseAPIURL: cfg.DatabaseAPI.URL,
		kafkaProducer:  kafkaProducer,
		timeout:        time.Duration(cfg.SeaweedFS.TimeoutSeconds) * time.Second,
		mockSleepTime:  100 * time.Millisecond, // Simulate upload time
	}, nil
}

// Upload simulates uploading an image to SeaweedFS and records it in the database
func (u *MockSeaweedFSUploader) Upload(ctx context.Context, processedImg *models.ProcessedImage) error {
	startTime := time.Now()

	logger := logging.WithFields(map[string]interface{}{
		"database_id": processedImg.Job.DatabaseID,
		"item_id":     processedImg.Job.ItemID,
		"image_url":   processedImg.Job.ImageURL,
	})

	logger.Info("Starting MOCK SeaweedFS upload (no actual upload)")

	// 1. MOCK: Simulate SeaweedFS upload with sleep
	fileName := u.generateFileName(processedImg)

	logger.WithFields(map[string]interface{}{
		"filename":   fileName,
		"size_bytes": len(processedImg.ImageData),
	}).Debug("Simulating SeaweedFS upload...")

	// Sleep to simulate upload time
	time.Sleep(u.mockSleepTime)
	// TODO: possibly record failure

	// Generate a mock file ID
	mockFileID := fmt.Sprintf("mock_%d_%d", time.Now().UnixNano(), processedImg.Job.ItemID)
	storagePath := u.generateStoragePath(processedImg, mockFileID)

	logger.WithFields(map[string]interface{}{
		"mock_file_id": mockFileID,
		"storage_path": storagePath,
		"simulated_ms": u.mockSleepTime.Milliseconds(),
	}).Info("MOCK upload completed (no actual upload to SeaweedFS)")

	// 2. Record success in the database (REAL API CALL)
	imageRecord := models.ImageCreate{
		Link: processedImg.Job.ImageURL,

		StorageCollection: "mock_collection",
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

	logger.Info("Making REAL API call to record image in database")
	err := u.recordImageInDB(ctx, imageRecord)
	if err != nil {
		logger.WithError(err).Error("Failed to record image in database")
		return fmt.Errorf("failed to record image in database: %w", err)
	}

	// Publish success message to Kafka
	successMsg := &models.UploadSuccessMessage{
		DatabaseID:        processedImg.Job.DatabaseID,
		ItemID:            processedImg.Job.ItemID,
		PropertyName:      processedImg.Job.PropertyName,
		ImageNumber:       processedImg.Job.ImageNumber,
		StorageCollection: "mock_collection",
		StoragePath:       storagePath,
		OriginalURL:       processedImg.Job.ImageURL,
		Width:             processedImg.Metadata.Width,
		Height:            processedImg.Metadata.Height,
		Extension:         processedImg.Metadata.Type,
		HashSum:           processedImg.Metadata.HashSum,
		UploadedAt:        time.Now().UTC().Format(time.RFC3339),
	}

	if err := u.kafkaProducer.PublishUploadSuccess(ctx, successMsg); err != nil {
		logger.WithError(err).Error("MOCK UPLOADER: Failed to publish upload success message to Kafka")
	}

	logger.WithField("duration_ms", time.Since(startTime).Milliseconds()).
		WithField("total_duration_ms", time.Since(processedImg.StartedAt).Milliseconds()).
		Info("MOCK upload and database recording completed successfully")

	return nil
}

// RecordFailure records a failed download/upload attempt in the database (REAL API CALL)
func (u *MockSeaweedFSUploader) RecordFailure(ctx context.Context, job models.ImageJob, reason string, status models.AttemptedAttemptStatus) error {
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

	url := u.databaseAPIURL + mockFailedDownloadEndpointPath
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

// recordImageInDB records the image metadata in the database (REAL API CALL)
func (u *MockSeaweedFSUploader) recordImageInDB(ctx context.Context, imageRecord models.ImageCreate) error {
	payload, err := json.Marshal(imageRecord)
	if err != nil {
		return fmt.Errorf("failed to marshal image record: %w", err)
	}

	url := u.databaseAPIURL + mockImageEndpointPath
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
func (u *MockSeaweedFSUploader) generateFileName(processedImg *models.ProcessedImage) string {
	imageNumStr := ""
	if processedImg.Job.ImageNumber != nil {
		imageNumStr = fmt.Sprintf("_%d", *processedImg.Job.ImageNumber)
	}

	return fmt.Sprintf("%s%s.%s",
		processedImg.Job.PropertyName,
		imageNumStr,
		processedImg.Metadata.Type,
	)
}

// generateStoragePath generates a storage path identifier
// Format: mock://seaweedfs/{mock_fid}
func (u *MockSeaweedFSUploader) generateStoragePath(processedImg *models.ProcessedImage, mockFID string) string {
	return fmt.Sprintf("mock://seaweedfs/%s", mockFID)
}

// Close closes the uploader and its resources
func (u *MockSeaweedFSUploader) Close() {
	if u.kafkaProducer != nil {
		u.kafkaProducer.Close()
	}
}
