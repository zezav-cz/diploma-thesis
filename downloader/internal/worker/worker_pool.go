package worker

import (
	"context"
	"fmt"
	"sync"

	"downloader/internal/config"
	"downloader/internal/downloader"
	"downloader/internal/logging"
	"downloader/internal/metrics"
	"downloader/internal/models"
	"downloader/internal/processor"
	"downloader/internal/uploader"

	"github.com/sirupsen/logrus"
)

type WorkerPool struct {
	jobsChan   chan models.ImageJob
	downloader *downloader.ImageDownloader
	metadata   *processor.MetadataExtractor
	uploader   uploader.Uploader
	numWorkers int
	wg         sync.WaitGroup
}

// Creates pool of workers
func NewWorkerPool(cfg *config.Config, jobsChan chan models.ImageJob) (*WorkerPool, error) {
	uploaderInstance, err := uploader.NewUploader(cfg)
	if err != nil {
		return nil, err
	}

	return &WorkerPool{
		jobsChan:   jobsChan,
		downloader: downloader.NewImageDownloader(cfg),
		metadata:   processor.NewMetadataExtractor(),
		uploader:   uploaderInstance,
		numWorkers: cfg.Downloader.MaxWorkers,
	}, nil
}

// Start starts the worker pool with the specified number of workers (goroutines)
func (wp *WorkerPool) Start(ctx context.Context) {
	logging.WithField("num_workers", wp.numWorkers).Info("Starting worker pool")

	// Start exactly numWorkers workers that will stay running
	for i := 0; i < wp.numWorkers; i++ {
		wp.wg.Add(1)
		go wp.worker(ctx, i)
	}
}

// Wait waits for all workers to finish
func (wp *WorkerPool) Wait() {
	logging.Debug("Waiting for all workers to stop")
	wp.wg.Wait()
	logging.Info("All workers stopped")
}

// Close closes the uploader and its resources
func (wp *WorkerPool) Close() {
	if wp.uploader != nil {
		wp.uploader.Close()
	}
}

// worker is a single goroutine that processes jobs
func (wp *WorkerPool) worker(ctx context.Context, workerID int) {
	defer wp.wg.Done()

	logger := logging.WithField("worker_id", workerID)
	logger.Info("Worker started")

	for {
		select {
		case <-ctx.Done():
			// Context cancelled - may lose pending jobs
			remaining := len(wp.jobsChan)
			if remaining > 0 {
				logger.WithField("pending_jobs", remaining).Warn("Context cancelled with pending jobs - data may be lost")
			} else {
				logger.Info("Context cancelled, no pending jobs")
			}
			logger.Info("Worker stopping due to context cancellation")
			return

		case job, ok := <-wp.jobsChan:
			if !ok {
				logger.Info("Jobs channel closed, worker stopping")
				return
			}

			// Process the job
			logger.Debug("Received job")
			wp.processJob(ctx, job)
		}
	}
}

// processJob processes a single job - downloads, extracts metadata, uploads
func (wp *WorkerPool) processJob(ctx context.Context, job models.ImageJob) {
	detail_logger := logging.WithFields(logrus.Fields{
		"database_id": job.DatabaseID,
		"item_id":     job.ItemID,
		"image_url":   job.ImageURL,
	})
	logging.Info("Processing job")

	// 1. Download image to memory
	processedImg, err := wp.downloader.Download(ctx, job)
	if err != nil {
		detail_logger.WithError(err).Error("Failed to download image")
		metrics.DownloadErrors.Inc()

		// Record failure in database
		if recordErr := wp.uploader.RecordFailure(ctx, job, fmt.Sprintf("Download failed: %v", err), models.AttemptStatusDownload); recordErr != nil {
			detail_logger.WithError(recordErr).Error("Failed to record download failure")
		}
		return
	}
	metrics.ImagesDownloaded.Inc()

	// 2. Extract metadata (width, height, type)
	err = wp.metadata.ExtractMetadata(processedImg)
	if err != nil {
		detail_logger.WithError(err).Error("Failed to extract metadata")
		metrics.ExtractionErrors.Inc()

		// Record failure in database
		if recordErr := wp.uploader.RecordFailure(ctx, job, fmt.Sprintf("Metadata extraction failed: %v", err), models.AttemptStatusMetadata); recordErr != nil {
			detail_logger.WithError(recordErr).Error("Failed to record extraction failure")
		}
		return
	}
	metrics.ImagesExtracted.Inc()

	// 3. Upload image + metadata
	err = wp.uploader.Upload(ctx, processedImg)
	if err != nil {
		detail_logger.WithError(err).Error("Failed to upload image")
		metrics.UploadErrors.Inc()
		// Failure is already recorded by the uploader
		return
	}
	metrics.ImagesUploaded.Inc()

	logging.Info("Job processed successfully")
}
