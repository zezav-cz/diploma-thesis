package uploader

import (
	"context"
	"fmt"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/models"
	"downloader/internal/producer"
)

// Uploader defines the interface for uploading images
type Uploader interface {
	// Upload uploads an image and records the result in the database
	Upload(ctx context.Context, processedImg *models.ProcessedImage) error

	// RecordFailure records a failed upload attempt
	RecordFailure(ctx context.Context, job models.ImageJob, reason string, status models.AttemptedAttemptStatus) error

	// Close closes any resources held by the uploader
	Close()
}

// NewUploader creates the appropriate uploader based on configuration
// Supports: seaweedfs, seaweedfs_mock, and fake uploaders
func NewUploader(cfg *config.Config) (Uploader, error) {
	// Create Kafka producer for upload success notifications
	kafkaProducer, err := producer.NewKafkaProducer(cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kafka producer: %w", err)
	}

	// Check for fake uploader first (console log only)
	if cfg.SeaweedFS.UseFake {
		logging.Warn("Using FAKE uploader (console log only, no uploads, no API calls)")
		return NewFakeUploader(cfg, kafkaProducer)
	}

	// Check for mock uploader (simulates upload, makes real API calls)
	if cfg.SeaweedFS.UseMock {
		logging.Warn("Using MOCK SeaweedFS uploader (simulates uploads, makes real API calls)")
		return NewMockSeaweedFSUploader(cfg, kafkaProducer)
	}

	// Check if SeaweedFS is properly configured
	if cfg.SeaweedFS.MasterURL == "" || cfg.SeaweedFS.FilerURL == "" {
		kafkaProducer.Close()
		return nil, fmt.Errorf("SeaweedFS is not configured: master_url and filer_url are required")
	}

	// Use real SeaweedFS uploader
	logging.Info("Using real SeaweedFS uploader")
	return NewSeaweedFSUploader(cfg, kafkaProducer)
}
