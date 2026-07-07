package consumer

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"
	"downloader/internal/metrics"
	"downloader/internal/models"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
)

type KafkaConsumer struct {
	consumer *kafka.Consumer
	jobsChan chan models.ImageJob
	cfg      *config.Config
}

func NewKafkaConsumer(cfg *config.Config, jobsChan chan models.ImageJob) (*KafkaConsumer, error) {
	configMap := &kafka.ConfigMap{
		"bootstrap.servers":             strings.Join(cfg.Kafka.Brokers, ","),
		"group.id":                      cfg.Kafka.ConsumerGroup,
		"auto.offset.reset":             "earliest",
		"enable.auto.commit":            true,
		"auto.commit.interval.ms":       5000,
		"session.timeout.ms":            10000,
		"heartbeat.interval.ms":         3000,
		"max.poll.interval.ms":          300000,
		"partition.assignment.strategy": "range",
		"log_level":                     0,
	}

	consumer, err := kafka.NewConsumer(configMap)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka consumer: %w", err)
	}

	err = consumer.SubscribeTopics([]string{cfg.Kafka.Topic}, func(c *kafka.Consumer, event kafka.Event) error {
		switch e := event.(type) {
		case kafka.AssignedPartitions:
			logging.WithField("partitions", e.Partitions).Info("Kafka partitions assigned")
			return c.Assign(e.Partitions)
		case kafka.RevokedPartitions:
			logging.WithField("partitions", e.Partitions).Info("Kafka partitions revoked")
			return c.Unassign()
		}
		return nil
	})
	if err != nil {
		consumer.Close()
		return nil, fmt.Errorf("failed to subscribe to topic: %w", err)
	}

	return &KafkaConsumer{
		consumer: consumer,
		jobsChan: jobsChan,
		cfg:      cfg,
	}, nil
}

// ensureConnection verifies connectivity. It retries with exponential backoff
// for up to 1 minute. If it cannot connect within that time, it returns an error.
func (kc *KafkaConsumer) ensureConnection(ctx context.Context) error {
	maxDuration := 1 * time.Minute
	startTime := time.Now()
	retryDelay := 1 * time.Second

	for {
		// Attempt to get metadata as a connectivity check
		// Timeout for the call itself is short (1s) to allow for the backoff loop to control timing
		_, err := kc.consumer.GetMetadata(nil, false, 1000)
		if err == nil {
			logging.Info("Kafka connection established/verified")
			return nil
		}

		// Check if we have exceeded the 1-minute limit
		if time.Since(startTime) > maxDuration {
			return fmt.Errorf("failed to connect to Kafka after %v: %w", maxDuration, err)
		}

		logging.
			WithError(err).
			WithField("retry_in", retryDelay.String()).
			Warn("Kafka unavailable, retrying...")

		// Wait for the backoff delay or context cancellation
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(retryDelay):
			// Exponential backoff: double the delay
			retryDelay *= 2
		}
	}
}

// Start begins consuming messages from Kafka
func (kc *KafkaConsumer) Start(ctx context.Context) error {
	logging.WithField("topic", kc.cfg.Kafka.Topic).Info("Starting Kafka consumer")

	// 1. Initial check: Ensure we are connected before starting the loop
	if err := kc.ensureConnection(ctx); err != nil {
		return err // "Die" if initial connection fails after 1m
	}

	for {
		select {
		case <-ctx.Done():
			logging.Info("Kafka consumer stopping due to context cancellation")
			return ctx.Err()
		default:
			// Poll for message
			msg, err := kc.consumer.ReadMessage(100) // 100ms timeout
			if err != nil {
				// Check if it's just a timeout (no message available)
				if kErr, ok := err.(kafka.Error); ok && kErr.Code() == kafka.ErrTimedOut {
					continue
				}

				// 2. Runtime Error: If we hit a real error, try to recover
				logging.WithError(err).Error("Error reading message from Kafka, checking connection...")

				// Enter recovery mode: Try for 1 minute
				if connErr := kc.ensureConnection(ctx); connErr != nil {
					// If we couldn't recover after 1 minute, we return the error (Die)
					logging.WithError(connErr).Error("Unrecoverable Kafka connection error")
					return connErr
				}

				// If we recovered, just continue the loop
				continue
			}

			// Parse message
			var job models.ImageJob
			if err := json.Unmarshal(msg.Value, &job); err != nil {
				logging.
					WithError(err).
					WithField("raw_message", string(msg.Value)).
					Error("Failed to unmarshal Kafka message")
				continue
			}

			// Increment consumed messages counter
			metrics.MessagesConsumed.WithLabelValues(*msg.TopicPartition.Topic, fmt.Sprintf("%d", msg.TopicPartition.Partition)).Inc()

			// Send to channel
			select {
			case kc.jobsChan <- job:
				logging.
					WithField("image_url", job.ImageURL).
					Debug("Job sent to processing channel")
			case <-ctx.Done():
				return ctx.Err()
			}
		}
	}
}

func (kc *KafkaConsumer) Close() error {
	logging.Info("Closing Kafka consumer")
	return kc.consumer.Close()
}
