package main

import (
	"context"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"downloader/internal/config"
	"downloader/internal/consumer"
	"downloader/internal/health"
	"downloader/internal/logging"
	"downloader/internal/metrics"
	"downloader/internal/models"
	"downloader/internal/worker"
)

type application struct {
	cfg                 *config.Config
	healthChecker       *health.HealthChecker
	healthCheckerServer *health.Server
	metricsServer       *metrics.Server
	kafkaConsumer       *consumer.KafkaConsumer
	workerPool          *worker.WorkerPool
	jobsChan            chan models.ImageJob
}

type serviceContexts struct {
	kafkaCtx      context.Context
	kafkaCancel   context.CancelFunc
	workerCtx     context.Context
	workerCancel  context.CancelFunc
	healthCtx     context.Context
	healthCancel  context.CancelFunc
	metricsCtx    context.Context
	metricsCancel context.CancelFunc
}

func main() {
	cfg := config.Get()
	logApplicationStart(cfg)

	app, cleanup := initializeApplication(cfg)
	defer cleanup()

	// Create separate contexts for each component
	kafkaCtx, kafkaCancel := context.WithCancel(context.Background())
	defer kafkaCancel()

	workerCtx, workerCancel := context.WithCancel(context.Background())
	defer workerCancel()

	healthCtx, healthCancel := context.WithCancel(context.Background())
	defer healthCancel()

	metricsCtx, metricsCancel := context.WithCancel(context.Background())
	defer metricsCancel()

	contexts := &serviceContexts{
		kafkaCtx:      kafkaCtx,
		kafkaCancel:   kafkaCancel,
		workerCtx:     workerCtx,
		workerCancel:  workerCancel,
		healthCtx:     healthCtx,
		healthCancel:  healthCancel,
		metricsCtx:    metricsCtx,
		metricsCancel: metricsCancel,
	}

	startupErrChan := startServices(contexts, app)

	waitForShutdownTrigger(startupErrChan)
	shutdownGracefully(contexts, app)
}

func logApplicationStart(cfg *config.Config) {
	logging.WithFields(cfg.GetMapOfConfig()).Trace("Config loaded successfully")
	logging.
		WithField("app_name", cfg.AppConfig.AppName).
		WithField("version", cfg.AppConfig.Version).
		Info("Application starting")
}

func initializeApplication(cfg *config.Config) (*application, func()) {
	jobsChan := make(chan models.ImageJob, cfg.Downloader.MaxWorkers*2)

	// HealthChecker
	healthChecker, err := health.NewHealthChecker(cfg)
	if err != nil {
		logging.WithError(err).Fatal("Failed to create health checker")
	}

	// HealthChecker server
	healthCheckerServer := health.NewServer(cfg, healthChecker)

	// Metrics server
	metricsServer := metrics.NewServer(cfg)

	// Consumer
	kafkaConsumer, err := consumer.NewKafkaConsumer(cfg, jobsChan)
	if err != nil {
		logging.WithError(err).Fatal("Failed to create Kafka consumer")
	}

	// Worker pool
	workerPool, err := worker.NewWorkerPool(cfg, jobsChan)
	if err != nil {
		logging.WithError(err).Fatal("Failed to create worker pool")
	}

	// Set initial metrics
	metrics.WorkersRunning.Set(float64(cfg.Downloader.MaxWorkers))

	healthChecker.SetStartup()
	logging.Info("Application initialized successfully")

	app := &application{
		cfg:                 cfg,
		healthChecker:       healthChecker,
		healthCheckerServer: healthCheckerServer,
		metricsServer:       metricsServer,
		kafkaConsumer:       kafkaConsumer,
		workerPool:          workerPool,
		jobsChan:            jobsChan,
	}

	cleanup := func() {
		healthChecker.Close()
		kafkaConsumer.Close()
	}

	return app, cleanup
}

func startServices(contexts *serviceContexts, app *application) chan error {
	var wg sync.WaitGroup
	startupErrChan := make(chan error, 3)

	// Start health checker server with its own context
	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := app.healthCheckerServer.Start(contexts.healthCtx); err != nil && err != context.Canceled {
			logging.WithError(err).Error("Health server error")
			app.healthChecker.SetNotAlive()
			select {
			case startupErrChan <- err:
			default:
			}
		}
	}()

	// Start metrics server with its own context
	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := app.metricsServer.Start(contexts.metricsCtx); err != nil && err != context.Canceled {
			logging.WithError(err).Error("Metrics server error")
			select {
			case startupErrChan <- err:
			default:
			}
		}
	}()

	// Start Kafka consumer with its own context
	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := app.kafkaConsumer.Start(contexts.kafkaCtx); err != nil && err != context.Canceled {
			logging.WithError(err).Error("Kafka consumer error")
			app.healthChecker.SetNotAlive()
			select {
			case startupErrChan <- err:
			default:
			}
		}
	}()

	// Start job channel size monitoring goroutine
	go monitorJobChannelSize(contexts.workerCtx, app.jobsChan)

	// Mark application as ready and start worker pool with its own context
	app.healthChecker.SetReady(true)
	app.workerPool.Start(contexts.workerCtx)
	logging.Info("Application running and ready - press Ctrl+C to stop")

	return startupErrChan
}

// monitorJobChannelSize periodically updates the job channel size metric
func monitorJobChannelSize(ctx context.Context, jobsChan chan models.ImageJob) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			metrics.JobChannelSize.Set(float64(len(jobsChan)))
		}
	}
}

func waitForShutdownTrigger(startupErrChan chan error) {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, os.Interrupt, syscall.SIGTERM)

	select {
	case sig := <-signalChan:
		logging.WithField("signal", sig.String()).Info("Shutdown signal received, gracefully stopping...")
	case err := <-startupErrChan:
		logging.WithError(err).Error("Server startup failed, initiating shutdown...")
	}
}

func shutdownGracefully(contexts *serviceContexts, app *application) {
	// STEP 1: Mark application as not ready (remove from load balancer)
	logging.Info("Marking application as not ready...")
	app.healthChecker.SetReady(false)

	// STEP 2: Stop Kafka consumer first to prevent new jobs from arriving
	logging.Info("Stopping Kafka consumer...")
	contexts.kafkaCancel()

	// STEP 3: Close jobs channel - signal workers that no more jobs will arrive
	logging.Info("Closing jobs channel...")
	close(app.jobsChan)

	// STEP 4: Wait for workers to finish processing remaining jobs
	logging.Info("Waiting for workers to finish processing remaining jobs...")
	app.workerPool.Wait()

	// STEP 5: Close worker pool resources (Kafka producer, etc.)
	logging.Info("Closing worker pool resources...")
	app.workerPool.Close()

	// STEP 6: Cancel worker context now that all work is done
	logging.Info("Stopping worker pool...")
	contexts.workerCancel()

	// STEP 7: Shutdown health server gracefully
	logging.Info("Shutting down health check server...")
	contexts.healthCancel()
	if err := app.healthCheckerServer.Shutdown(context.Background()); err != nil {
		logging.WithError(err).Error("Error shutting down health server")
	}

	// STEP 8: Shutdown metrics server gracefully
	logging.Info("Shutting down metrics server...")
	contexts.metricsCancel()
	if err := app.metricsServer.Shutdown(context.Background()); err != nil {
		logging.WithError(err).Error("Error shutting down metrics server")
	}

	logging.Info("Application stopped gracefully - all jobs processed")
}
