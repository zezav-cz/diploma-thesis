package health

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"
)

// Server is an HTTP server for health check endpoints
type Server struct {
	checker *HealthChecker
	server  *http.Server
	cfg     *config.Config
}

// NewServer creates a new health check HTTP server
func NewServer(cfg *config.Config, checker *HealthChecker) *Server {
	mux := http.NewServeMux()

	s := &Server{
		checker: checker,
		cfg:     cfg,
		server: &http.Server{
			Addr:         fmt.Sprintf(":%d", cfg.Health.Port),
			Handler:      mux,
			ReadTimeout:  10 * time.Second,
			WriteTimeout: 10 * time.Second,
		},
	}

	// Register endpoints
	mux.HandleFunc("/healthz", s.handleLiveness)
	mux.HandleFunc("/readyz", s.handleReadiness)
	mux.HandleFunc("/startupz", s.handleStartup)

	return s
}

// Start starts the HTTP server
func (s *Server) Start(ctx context.Context) error {
	logging.WithField("port", s.cfg.Health.Port).Info("Starting health check server")

	errChan := make(chan error, 1)

	go func() {
		if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errChan <- err
		}
	}()

	select {
	case err := <-errChan:
		return fmt.Errorf("health server failed to start: %w", err)
	case <-ctx.Done():
		return s.Shutdown(context.Background())
	case <-time.After(100 * time.Millisecond):
		// Server started successfully
		return nil
	}
}

// Shutdown gracefully shuts down the HTTP server
func (s *Server) Shutdown(ctx context.Context) error {
	logging.Info("Shutting down health check server")

	shutdownCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	return s.server.Shutdown(shutdownCtx)
}

// handleLiveness handles the liveness probe endpoint
// GET /healthz
// Kubernetes uses this endpoint to detect if the application is alive
// If it fails, the pod will be restarted
func (s *Server) handleLiveness(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	result := s.checker.CheckLiveness(ctx)

	s.writeResponse(w, result)
}

// handleReadiness handles the readiness probe endpoint
// GET /readyz
// Kubernetes uses this endpoint to detect if the application is ready
// If it fails, the pod will be removed from the load balancer
func (s *Server) handleReadiness(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	result := s.checker.CheckReadiness(ctx)

	s.writeResponse(w, result)
}

// handleStartup handles the startup probe endpoint
// GET /startupz
// Kubernetes uses this endpoint to detect if the application has completed startup
// Until it succeeds, other probes (liveness/readiness) are disabled
func (s *Server) handleStartup(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	result := s.checker.CheckStartup(ctx)

	s.writeResponse(w, result)
}

// writeResponse writes CheckResult as HTTP response
func (s *Server) writeResponse(w http.ResponseWriter, result CheckResult) {
	w.Header().Set("Content-Type", "application/json")

	// Set HTTP status code based on health status
	statusCode := http.StatusOK
	if result.Status == StatusUnhealthy {
		statusCode = http.StatusServiceUnavailable
	} else if result.Status == StatusStarting {
		statusCode = http.StatusOK // return 200 during startup
	}

	w.WriteHeader(statusCode)

	if err := json.NewEncoder(w).Encode(result); err != nil {
		logging.WithError(err).Error("Failed to encode health check response")
	}
}
