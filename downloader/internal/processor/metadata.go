package processor

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"image"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"

	"downloader/internal/logging"
	"downloader/internal/models"

	_ "golang.org/x/image/webp"
)

type MetadataExtractor struct{}

func NewMetadataExtractor() *MetadataExtractor {
	return &MetadataExtractor{}
}

// ExtractMetadata extracts width, height and type from the image in memory
func (m *MetadataExtractor) ExtractMetadata(processedImg *models.ProcessedImage) error {
	// Create reader from byte slice
	reader := bytes.NewReader(processedImg.ImageData)

	// DecodeConfig is efficient - reads only the header, not the whole image
	config, format, err := image.DecodeConfig(reader)
	if err != nil {
		return fmt.Errorf("failed to decode image config: %w", err)
	}

	// Calculate SHA-256 hash of image data
	hash := sha256.Sum256(processedImg.ImageData)
	hashString := "sha256:" + hex.EncodeToString(hash[:])

	// Populate metadata
	processedImg.Metadata = models.ImageMetadata{
		Width:   config.Width,
		Height:  config.Height,
		Type:    format, // jpeg, png, gif, webp
		HashSum: hashString,
	}

	logging.
		WithField("width", config.Width).
		WithField("height", config.Height).
		WithField("type", format).
		WithField("hashsum", hashString).
		Debug("Metadata extracted successfully")

	return nil
}
