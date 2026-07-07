package downloader

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/models"
)

type ImageDownloader struct {
	client *http.Client
	cfg    *config.Config
}

// NewImageDownloader creates a new downloader with a timeout
func NewImageDownloader(cfg *config.Config) *ImageDownloader {
	return &ImageDownloader{
		client: &http.Client{
			Timeout: time.Duration(cfg.Downloader.TimeoutSeconds) * time.Second,
		},
		cfg: cfg,
	}
}

// Download downloads an image from a URL into memory (byte buffer)
func (d *ImageDownloader) Download(ctx context.Context, job models.ImageJob) (*models.ProcessedImage, error) {
	startTime := time.Now()

	logging.
		WithField("customer_id", job.DatabaseID).
		WithField("item_id", job.ItemID).
		WithField("property_name", job.PropertyName).
		WithField("image_number", job.ImageNumber).
		WithField("url", job.ImageURL).
		Debug("Starting image download")

	// Create request with context
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, job.ImageURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Make HTTP request
	resp, err := d.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to download image: %w", err)
	}
	defer resp.Body.Close()

	// Check HTTP status
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	// Read the entire image into memory (buffer)
	// bytes.Buffer is efficient for holding data in RAM
	var buf bytes.Buffer
	_, err = io.Copy(&buf, resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read image data: %w", err)
	}

	imageData := buf.Bytes()

	logging.
		WithField("customer_id", job.DatabaseID).
		WithField("item_id", job.ItemID).
		WithField("property_name", job.PropertyName).
		WithField("image_number", job.ImageNumber).
		WithField("size_bytes", len(imageData)).
		WithField("duration_ms", time.Since(startTime).Milliseconds()).
		Info("Image downloaded successfully")

	return &models.ProcessedImage{
		ImageData: imageData,
		Job:       job,
		StartedAt: startTime,
		// Metadata will be populated later
	}, nil
}
