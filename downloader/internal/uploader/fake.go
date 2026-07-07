package uploader

import (
	"context"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/models"
	"downloader/internal/producer"
)

// FakeUploader is a fake uploader that only logs to console without making any actual uploads or API calls
type FakeUploader struct {
	// Kafka producer for success notifications
	kafkaProducer *producer.KafkaProducer

	// Configuration
	mockSleepTime time.Duration
}

// NewFakeUploader creates a new fake uploader
func NewFakeUploader(cfg *config.Config, kafkaProducer *producer.KafkaProducer) (*FakeUploader, error) {
	return &FakeUploader{
		kafkaProducer: kafkaProducer,
		mockSleepTime: 50 * time.Millisecond, // Simulate some processing time
	}, nil
}

// Upload simulates uploading an image by only logging to console
func (u *FakeUploader) Upload(ctx context.Context, processedImg *models.ProcessedImage) error {
	startTime := time.Now()

	logger := logging.WithFields(map[string]interface{}{
		"database_id":   processedImg.Job.DatabaseID,
		"item_id":       processedImg.Job.ItemID,
		"image_url":     processedImg.Job.ImageURL,
		"property_name": processedImg.Job.PropertyName,
		"image_number":  processedImg.Job.ImageNumber,
	})

	logger.Info("FAKE UPLOADER: Starting fake upload (console log only)")

	// Simulate processing time
	time.Sleep(u.mockSleepTime)

	// Generate fake storage path
	storagePath := "fake://mock-storage-path"

	logger.WithFields(map[string]interface{}{
		"width":             processedImg.Metadata.Width,
		"height":            processedImg.Metadata.Height,
		"format":            processedImg.Metadata.Type,
		"size_bytes":        len(processedImg.ImageData),
		"duration_ms":       time.Since(startTime).Milliseconds(),
		"total_duration_ms": time.Since(processedImg.StartedAt).Milliseconds(),
	}).Info("FAKE UPLOADER: Upload completed (no actual upload, no API calls)")

	// Publish success message to Kafka
	successMsg := &models.UploadSuccessMessage{
		DatabaseID:        processedImg.Job.DatabaseID,
		ItemID:            processedImg.Job.ItemID,
		PropertyName:      processedImg.Job.PropertyName,
		ImageNumber:       processedImg.Job.ImageNumber,
		StorageCollection: "fake_collection",
		StoragePath:       storagePath,
		OriginalURL:       processedImg.Job.ImageURL,
		Width:             processedImg.Metadata.Width,
		Height:            processedImg.Metadata.Height,
		Extension:         processedImg.Metadata.Type,
		HashSum:           processedImg.Metadata.HashSum,
		UploadedAt:        time.Now().UTC().Format(time.RFC3339),
	}

	if err := u.kafkaProducer.PublishUploadSuccess(ctx, successMsg); err != nil {
		logger.WithError(err).Error("FAKE UPLOADER: Failed to publish upload success message to Kafka")
	}

	return nil
}

// RecordFailure simulates recording a failure by only logging to console
func (u *FakeUploader) RecordFailure(ctx context.Context, job models.ImageJob, reason string, status models.AttemptedAttemptStatus) error {
	logger := logging.WithFields(map[string]interface{}{
		"database_id":   job.DatabaseID,
		"item_id":       job.ItemID,
		"image_url":     job.ImageURL,
		"property_name": job.PropertyName,
		"image_number":  job.ImageNumber,
		"reason":        reason,
	})

	logger.Warn("FAKE UPLOADER: Recording failure (console log only)")

	return nil
}

// Close closes the uploader and its resources
func (u *FakeUploader) Close() {
	if u.kafkaProducer != nil {
		u.kafkaProducer.Close()
	}
}
