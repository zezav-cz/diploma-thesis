package producer

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/models"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
)

// KafkaProducer handles producing messages to Kafka
type KafkaProducer struct {
	producer *kafka.Producer
	topic    string
	cfg      *config.Config
}

// NewKafkaProducer creates a new Kafka producer
func NewKafkaProducer(cfg *config.Config) (*KafkaProducer, error) {
	configMap := &kafka.ConfigMap{
		"bootstrap.servers": strings.Join(cfg.Kafka.Brokers, ","),
		"acks":              "all",
		"retries":           3,
		"log_level":         0,
	}

	producer, err := kafka.NewProducer(configMap)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka producer: %w", err)
	}

	// Start a goroutine to handle delivery reports
	go func() {
		for e := range producer.Events() {
			switch ev := e.(type) {
			case *kafka.Message:
				if ev.TopicPartition.Error != nil {
					logging.WithError(ev.TopicPartition.Error).
						WithField("topic", *ev.TopicPartition.Topic).
						Error("Failed to deliver message to Kafka")
				} else {
					logging.WithFields(map[string]interface{}{
						"topic":     *ev.TopicPartition.Topic,
						"partition": ev.TopicPartition.Partition,
						"offset":    ev.TopicPartition.Offset,
					}).Debug("Message delivered to Kafka")
				}
			}
		}
	}()

	return &KafkaProducer{
		producer: producer,
		topic:    cfg.Kafka.ProducerTopic,
		cfg:      cfg,
	}, nil
}

// PublishUploadSuccess publishes a message about a successful image upload
func (kp *KafkaProducer) PublishUploadSuccess(ctx context.Context, msg *models.UploadSuccessMessage) error {
	payload, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("failed to marshal upload success message: %w", err)
	}

	logger := logging.WithFields(map[string]interface{}{
		"topic":       kp.topic,
		"database_id": msg.DatabaseID,
		"item_id":     msg.ItemID,
	})

	logger.Debug("Publishing upload success message to Kafka")

	deliveryChan := make(chan kafka.Event)
	defer close(deliveryChan)

	err = kp.producer.Produce(&kafka.Message{
		TopicPartition: kafka.TopicPartition{Topic: &kp.topic, Partition: kafka.PartitionAny},
		Value:          payload,
		Key:            []byte(fmt.Sprintf("%s-%d", msg.DatabaseID, msg.ItemID)),
	}, deliveryChan)

	if err != nil {
		return fmt.Errorf("failed to produce message: %w", err)
	}

	// Wait for delivery confirmation
	select {
	case <-ctx.Done():
		return ctx.Err()
	case e := <-deliveryChan:
		m := e.(*kafka.Message)
		if m.TopicPartition.Error != nil {
			return fmt.Errorf("delivery failed: %w", m.TopicPartition.Error)
		}
		logger.WithFields(map[string]interface{}{
			"partition": m.TopicPartition.Partition,
			"offset":    m.TopicPartition.Offset,
		}).Info("Upload success message published to Kafka")
	}

	return nil
}

// Close closes the producer
func (kp *KafkaProducer) Close() {
	logging.Info("Closing Kafka producer")
	// Wait for outstanding messages to be delivered
	kp.producer.Flush(5000) // 5 second timeout
	kp.producer.Close()
}
