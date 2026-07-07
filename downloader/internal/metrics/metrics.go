package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

const (
	prefix = "image_downloader_"
)

var (
	// Messages consumed from Kafka
	MessagesConsumed = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: prefix + "messages_consumed_total",
		Help: "Total number of messages consumed from Kafka",
	}, []string{"topic", "partition"})

	// Job channel size (gauge)
	JobChannelSize = promauto.NewGauge(prometheus.GaugeOpts{
		Name: prefix + "job_channel_size",
		Help: "Current number of jobs in the job channel",
	})

	// Number of workers running (constant gauge)
	WorkersRunning = promauto.NewGauge(prometheus.GaugeOpts{
		Name: prefix + "workers_running",
		Help: "Number of worker goroutines currently running",
	})

	// Images downloaded successfully
	ImagesDownloaded = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "images_downloaded_total",
		Help: "Total number of images successfully downloaded",
	})

	// Images extracted (metadata extracted successfully)
	ImagesExtracted = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "images_extracted_total",
		Help: "Total number of images with metadata successfully extracted",
	})

	// Images uploaded successfully
	ImagesUploaded = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "images_uploaded_total",
		Help: "Total number of images successfully uploaded",
	})

	// Download errors
	DownloadErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "download_errors_total",
		Help: "Total number of errors during image download",
	})

	// Extraction errors
	ExtractionErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "extraction_errors_total",
		Help: "Total number of errors during metadata extraction",
	})

	// Upload errors
	UploadErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: prefix + "upload_errors_total",
		Help: "Total number of errors during image upload",
	})
)
