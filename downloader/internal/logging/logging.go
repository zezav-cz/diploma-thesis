package logging

import (
	"io"
	"os"
	"sync"

	"downloader/internal/config"

	nested "github.com/antonfisher/nested-logrus-formatter"
	"github.com/sirupsen/logrus"
)

var (
	logger *logrus.Logger
	once   sync.Once
)

// Get returns a singleton instance of the configured logrus logger
func Get() *logrus.Logger {
	once.Do(func() {
		logger = initLogger()
	})
	return logger
}

// initLogger creates and configures a new logrus logger based on the config
func initLogger() *logrus.Logger {
	cfg := config.Get()
	log := logrus.New()

	log.AddHook(&GoroutineHook{})

	// Set log level
	switch cfg.Logging.Level {
	case config.DebugLevel:
		log.SetLevel(logrus.DebugLevel)
	case config.InfoLevel:
		log.SetLevel(logrus.InfoLevel)
	case config.WarnLevel:
		log.SetLevel(logrus.WarnLevel)
	case config.ErrorLevel:
		log.SetLevel(logrus.ErrorLevel)
	case config.TraceLevel:
		log.SetLevel(logrus.TraceLevel)
	default:
		log.SetLevel(logrus.InfoLevel)
		defer log.Warnf("unknown log level %s, defaulting to InfoLevel", cfg.Logging.Level)
	}

	// Set log format
	switch cfg.Logging.Format {
	case config.JsonFormat:
		log.SetFormatter(&logrus.JSONFormatter{})
	case config.TextFormat:
		log.SetFormatter(&nested.Formatter{
			NoColors:        false,
			TimestampFormat: "2006-01-02 15:04:05",
			TrimMessages:    true,
		})
	default:
		log.SetFormatter(&logrus.TextFormatter{
			FullTimestamp: true,
		})
		defer log.Warnf("unknown log format %s, defaulting to TextFormat", cfg.Logging.Format)
	}

	// Set output to stdout
	log.SetOutput(os.Stdout)

	return log
}

// WithFields creates a new logger entry with the provided fields
func WithFields(fields logrus.Fields) *logrus.Entry {
	return Get().WithFields(fields)
}

// WithField creates a new logger entry with a single field
func WithField(key string, value interface{}) *logrus.Entry {
	return Get().WithField(key, value)
}

// WithError creates a new logger entry with an error field
func WithError(err error) *logrus.Entry {
	return Get().WithError(err)
}

// SetOutput sets the output destination for the logger
func SetOutput(output io.Writer) {
	Get().SetOutput(output)
}

// Debug logs a message at debug level
func Debug(args ...interface{}) {
	Get().Debug(args...)
}

// Debugf logs a formatted message at debug level
func Debugf(format string, args ...interface{}) {
	Get().Debugf(format, args...)
}

// Info logs a message at info level
func Info(args ...interface{}) {
	Get().Info(args...)
}

// Infof logs a formatted message at info level
func Infof(format string, args ...interface{}) {
	Get().Infof(format, args...)
}

// Warn logs a message at warn level
func Warn(args ...interface{}) {
	Get().Warn(args...)
}

// Warnf logs a formatted message at warn level
func Warnf(format string, args ...interface{}) {
	Get().Warnf(format, args...)
}

// Error logs a message at error level
func Error(args ...interface{}) {
	Get().Error(args...)
}

// Errorf logs a formatted message at error level
func Errorf(format string, args ...interface{}) {
	Get().Errorf(format, args...)
}

// Fatal logs a message at fatal level and exits
func Fatal(args ...interface{}) {
	Get().Fatal(args...)
}

// Fatalf logs a formatted message at fatal level and exits
func Fatalf(format string, args ...interface{}) {
	Get().Fatalf(format, args...)
}
