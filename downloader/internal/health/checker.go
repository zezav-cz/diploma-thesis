package health

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"

	"github.com/confluentinc/confluent-kafka-go/v2/kafka"
)

// Status represents the state of the health check
type Status string

const (
	StatusHealthy   Status = "healthy"
	StatusUnhealthy Status = "unhealthy"
	StatusStarting  Status = "starting"
)

// CheckResult represents the result of the health check
type CheckResult struct {
	Status  Status `json:"status"`
	Message string `json:"message,omitempty"`
}

// HealthChecker monitors the health of components
type HealthChecker struct {
	cfg             *config.Config
	kafkaAdmin      *kafka.AdminClient
	mu              sync.RWMutex
	isReady         bool
	startupComplete bool
	isAlive         bool
}

// NewHealthChecker creates a new health checker
func NewHealthChecker(cfg *config.Config) (*HealthChecker, error) {
	// Create Kafka admin client for health checks
	adminConfig := &kafka.ConfigMap{
		"bootstrap.servers": strings.Join(cfg.Kafka.Brokers, ","),
		"log_level":         0,
	}
	adminClient, err := kafka.NewAdminClient(adminConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create kafka admin client: %w", err)
	}

	if err := CheckStartupIndicatorNotExists(); err != nil {
		return nil, err
	}

	return &HealthChecker{
		cfg:             cfg,
		kafkaAdmin:      adminClient,
		isReady:         false,
		startupComplete: false,
		isAlive:         true, // Start as alive
	}, nil
}

// Close closes the health checker
func (h *HealthChecker) Close() {
	if h.kafkaAdmin != nil {
		h.kafkaAdmin.Close()
	}
	// Remove startup indicator on exit
	_ = RemoveStartupIndicator()
}

// SetReady sets the application as ready (for readiness probe)
func (h *HealthChecker) SetReady(ready bool) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.isReady = ready
}

// IsReady returns whether the application is ready
func (h *HealthChecker) IsReady() bool {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.isReady
}

// SetNotAlive sets the application as not alive (for liveness probe)
// Causes the liveness probe to fail and Kubernetes to restart the pod
func (h *HealthChecker) SetNotAlive() {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.isAlive = false
}

// SetStartup sets startup as complete (for startup probe)
// Once set to true, it remains true forever
// Also creates startup indicator file /tmp/start
func (h *HealthChecker) SetStartup() {
	h.mu.Lock()
	defer h.mu.Unlock()

	if !h.startupComplete {
		h.startupComplete = true
		// Create startup indicator file
		_ = CreateStartupIndicator()
	}
}

// CheckStartup checks if the application has completed startup
// Used for Kubernetes startup probe
func (h *HealthChecker) CheckStartup(ctx context.Context) CheckResult {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if h.startupComplete {
		return CheckResult{
			Status:  StatusHealthy,
			Message: "startup complete",
		}
	}

	return CheckResult{
		Status:  StatusStarting,
		Message: "starting",
	}
}

// CheckLiveness checks if the application is alive
// Used for Kubernetes liveness probe (restarts pod on failure)
func (h *HealthChecker) CheckLiveness(ctx context.Context) CheckResult {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if !h.isAlive {
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: "not alive",
		}
	}

	return CheckResult{
		Status:  StatusHealthy,
		Message: "alive",
	}
}

// CheckReadiness checks if the application is ready to accept traffic
// Used for Kubernetes readiness probe (removes from LB on failure)
func (h *HealthChecker) CheckReadiness(ctx context.Context) CheckResult {
	// Check if the application was marked as ready
	if !h.IsReady() {
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: "not ready yet",
		}
	}

	// Check Kafka connection
	kafkaResult := h.checkKafka(ctx)
	if kafkaResult.Status != StatusHealthy {
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: fmt.Sprintf("kafka: %s", kafkaResult.Message),
		}
	}

	return CheckResult{
		Status:  StatusHealthy,
		Message: "ready",
	}
}

// checkKafka checks Kafka connection
func (h *HealthChecker) checkKafka(ctx context.Context) CheckResult {
	checkCtx, cancel := context.WithTimeout(ctx, time.Duration(h.cfg.Health.KafkaCheckTimeout)*time.Second)
	defer cancel()

	// Try to get metadata from Kafka
	metadata, err := h.kafkaAdmin.GetMetadata(nil, false, int(h.cfg.Health.KafkaCheckTimeout*1000))
	if err != nil {
		logging.WithError(err).Debug("Kafka health check failed")
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: fmt.Sprintf("kafka connection failed: %v", err),
		}
	}

	// Check if brokers exist
	if len(metadata.Brokers) == 0 {
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: "no kafka brokers available",
		}
	}

	select {
	case <-checkCtx.Done():
		return CheckResult{
			Status:  StatusUnhealthy,
			Message: "kafka check timeout",
		}
	default:
		logging.WithField("brokers_count", len(metadata.Brokers)).Debug("Kafka health check passed")
		return CheckResult{
			Status:  StatusHealthy,
			Message: fmt.Sprintf("%d brokers available", len(metadata.Brokers)),
		}
	}
}
