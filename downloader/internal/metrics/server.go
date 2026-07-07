package metrics

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"downloader/internal/config"
	"downloader/internal/logging"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Server struct {
	server *http.Server
	cfg    *config.Config
}

func NewServer(cfg *config.Config) *Server {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())

	return &Server{
		server: &http.Server{
			Addr:    fmt.Sprintf(":%d", cfg.Metrics.Port),
			Handler: mux,
		},
		cfg: cfg,
	}
}

func (s *Server) Start(ctx context.Context) error {
	logging.WithField("port", s.cfg.Metrics.Port).Info("Starting metrics server")

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := s.server.Shutdown(shutdownCtx); err != nil {
			logging.WithError(err).Error("Error shutting down metrics server")
		}
	}()

	if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("metrics server error: %w", err)
	}
	return nil
}

func (s *Server) Shutdown(ctx context.Context) error {
	logging.Info("Shutting down metrics server")
	return s.server.Shutdown(ctx)
}
