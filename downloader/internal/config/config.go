package config

import (
	"fmt"
	"strings"
	"sync"

	"errors"

	"github.com/spf13/viper"
)

// --- Enums & Constants ---
type LogLevel string
type LogFormat string

const (
	InfoLevel   LogLevel  = "info"
	DebugLevel            = "debug"
	WarnLevel             = "warn"
	ErrorLevel            = "error"
	TraceLevel            = "trace"
	JsonFormat  LogFormat = "json"
	TextFormat            = "txt"
	APP_NAME              = "image-downloader"
	APP_VERSION           = "0.1.0"
)

// --- Structs

type AppConfig struct {
	AppName string
	Version string
}

type LoggingConfig struct {
	Level  LogLevel  `mapstructure:"level"`
	Format LogFormat `mapstructure:"format"`
}

func (lc *LoggingConfig) Validate() error {
	var errs error

	switch lc.Level {
	case InfoLevel, DebugLevel, WarnLevel, ErrorLevel, TraceLevel:
	default:
		er := fmt.Errorf("invalid log level: %s", lc.Level)
		errs = errors.Join(errs, er)
	}

	switch lc.Format {
	case JsonFormat, TextFormat:
	default:
		er := fmt.Errorf("invalid log format: %s", lc.Format)
		errs = errors.Join(errs, er)
	}
	return errs
}

type DownloaderConfig struct {
	MaxWorkers     int `mapstructure:"max_workers"`
	TimeoutSeconds int `mapstructure:"timeout_seconds"`
}

func (dc *DownloaderConfig) Validate() error {
	var errs error
	if dc.MaxWorkers <= 0 {
		errs = errors.Join(errs, fmt.Errorf("downloader max_workers must be greater than 0"))
	}
	if dc.TimeoutSeconds <= 0 {
		errs = errors.Join(errs, fmt.Errorf("downloader timeout_seconds must be greater than 0"))
	}
	return errs
}

type SeaweedFSConfig struct {
	MasterURL      string `mapstructure:"master_url"`
	FilerURL       string `mapstructure:"filer_url"`
	TimeoutSeconds int    `mapstructure:"timeout_seconds"`
	ChunkSizeMB    int    `mapstructure:"chunk_size_mb"`
	UseMock        bool   `mapstructure:"use_mock"` // Use mock uploader for testing API calls without SeaweedFS
	UseFake        bool   `mapstructure:"use_fake"` // Use fake uploader for console logging only (no uploads, no API calls)
}

func (sc *SeaweedFSConfig) Validate() error {
	var errs error

	if sc.UseMock || sc.UseFake {
		return nil
	}

	if sc.MasterURL == "" {
		errs = errors.Join(errs, fmt.Errorf("seaweedfs master_url cannot be empty"))
	}
	if sc.FilerURL == "" {
		errs = errors.Join(errs, fmt.Errorf("seaweedfs filer_url cannot be empty"))
	}
	if sc.TimeoutSeconds <= 0 {
		errs = errors.Join(errs, fmt.Errorf("seaweedfs timeout_seconds must be greater than 0"))
	}
	if sc.ChunkSizeMB <= 0 {
		errs = errors.Join(errs, fmt.Errorf("seaweedfs chunk_size_mb must be greater than 0"))
	}
	return errs
}

type DatabaseAPIConfig struct {
	URL string `mapstructure:"url"`
}

func (dc *DatabaseAPIConfig) Validate() error {
	var errs error
	if dc.URL == "" {
		errs = errors.Join(errs, fmt.Errorf("database_api url cannot be empty"))
	}
	return errs
}

type KafkaConfig struct {
	Brokers       []string `mapstructure:"brokers"`
	Topic         string   `mapstructure:"topic"`
	ProducerTopic string   `mapstructure:"producer_topic"`
	ConsumerGroup string   `mapstructure:"consumer_group"`
}

type HealthConfig struct {
	Port               int `mapstructure:"port"`
	KafkaCheckTimeout  int `mapstructure:"kafka_check_timeout_seconds"`
	StartupGracePeriod int `mapstructure:"startup_grace_period_seconds"`
}

func (hc *HealthConfig) Validate() error {
	var errs error
	if hc.Port <= 0 || hc.Port > 65535 {
		errs = errors.Join(errs, fmt.Errorf("health port must be between 1 and 65535"))
	}
	if hc.KafkaCheckTimeout <= 0 {
		errs = errors.Join(errs, fmt.Errorf("health kafka_check_timeout_seconds must be greater than 0"))
	}
	if hc.StartupGracePeriod < 0 {
		errs = errors.Join(errs, fmt.Errorf("health startup_grace_period_seconds must be non-negative"))
	}
	return errs
}

type MetricsConfig struct {
	Port int `mapstructure:"port"`
}

func (mc *MetricsConfig) Validate() error {
	var errs error
	if mc.Port <= 0 || mc.Port > 65535 {
		errs = errors.Join(errs, fmt.Errorf("metrics port must be between 1 and 65535"))
	}
	return errs
}

func (kc *KafkaConfig) Validate() error {
	var errs error
	if len(kc.Brokers) == 0 {
		errs = errors.Join(errs, fmt.Errorf("kafka brokers cannot be empty"))
	}
	if kc.Topic == "" {
		errs = errors.Join(errs, fmt.Errorf("kafka topic cannot be empty"))
	}
	if kc.ProducerTopic == "" {
		errs = errors.Join(errs, fmt.Errorf("kafka producer_topic cannot be empty"))
	}
	if kc.ConsumerGroup == "" {
		errs = errors.Join(errs, fmt.Errorf("kafka consumer group cannot be empty"))
	}
	return errs
}

type Config struct {
	Logging     LoggingConfig     `mapstructure:"logging"`
	Downloader  DownloaderConfig  `mapstructure:"downloader"`
	SeaweedFS   SeaweedFSConfig   `mapstructure:"seaweedfs"`
	DatabaseAPI DatabaseAPIConfig `mapstructure:"database_api"`
	Kafka       KafkaConfig       `mapstructure:"kafka"`
	Health      HealthConfig      `mapstructure:"health"`
	Metrics     MetricsConfig     `mapstructure:"metrics"`
	AppConfig   AppConfig
}

// -- Global State

var (
	instance *Config
	once     sync.Once
)

// -- Validators

func (c *Config) Validate() error {
	var errs error
	errs = errors.Join(errs, c.Logging.Validate())
	errs = errors.Join(errs, c.Kafka.Validate())
	errs = errors.Join(errs, c.Downloader.Validate())
	errs = errors.Join(errs, c.SeaweedFS.Validate())
	errs = errors.Join(errs, c.DatabaseAPI.Validate())
	errs = errors.Join(errs, c.Health.Validate())
	errs = errors.Join(errs, c.Metrics.Validate())
	return errs
}

// -- Logic

func Get() *Config {
	once.Do(func() {
		var err error
		instance, err = loadConfig()
		if err != nil {
			panic(fmt.Errorf("failed to load config:\n%w", err))
		}
	})
	return instance
}

func loadConfig() (*Config, error) {
	var cfg Config
	v := viper.New()

	v.SetDefault("logging.level", InfoLevel)
	v.SetDefault("logging.format", TextFormat)
	v.SetDefault("downloader.max_workers", 10)
	v.SetDefault("downloader.timeout_seconds", 30)
	v.SetDefault("seaweedfs.timeout_seconds", 30)
	v.SetDefault("seaweedfs.chunk_size_mb", 2)
	v.SetDefault("seaweedfs.use_mock", false)
	v.SetDefault("seaweedfs.use_fake", false)
	v.SetDefault("kafka.topic", "image-downloads")
	v.SetDefault("kafka.producer_topic", "embeder")
	v.SetDefault("kafka.consumer_group", "image-downloader-group")
	v.SetDefault("health.port", 8081)
	v.SetDefault("health.kafka_check_timeout_seconds", 5)
	v.SetDefault("health.startup_grace_period_seconds", 30)
	v.SetDefault("metrics.port", 9090)

	v.SetConfigName(".env")
	v.SetConfigType("env")
	v.AutomaticEnv()
	v.AddConfigPath(".")

	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	// Explicitly bind kafka.brokers to handle comma-separated env var
	v.BindEnv("kafka.brokers")
	v.BindEnv("database_api.url")
	v.BindEnv("seaweedfs.master_url")
	v.BindEnv("seaweedfs.filer_url")
	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("error reading config file: %w", err)
		}
	}

	// Normalize log level and format to lowercase for case-insensitive handling
	if v.IsSet("logging.level") {
		v.Set("logging.level", strings.ToLower(v.GetString("logging.level")))
	}
	if v.IsSet("logging.format") {
		v.Set("logging.format", strings.ToLower(v.GetString("logging.format")))
	}

	// 5. Unmarshal into Struct
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unable to decode into struct: %w", err)
	}
	cfg.AppConfig = AppConfig{
		AppName: APP_NAME,
		Version: APP_VERSION,
	}

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	return &cfg, nil
}

func (c *Config) GetMapOfConfig() map[string]interface{} {
	return map[string]interface{}{
		"logging.level":                       c.Logging.Level,
		"logging.format":                      c.Logging.Format,
		"downloader.max_workers":              c.Downloader.MaxWorkers,
		"downloader.timeout_seconds":          c.Downloader.TimeoutSeconds,
		"seaweedfs.master_url":                c.SeaweedFS.MasterURL,
		"seaweedfs.filer_url":                 c.SeaweedFS.FilerURL,
		"seaweedfs.timeout_seconds":           c.SeaweedFS.TimeoutSeconds,
		"seaweedfs.chunk_size_mb":             c.SeaweedFS.ChunkSizeMB,
		"seaweedfs.use_mock":                  c.SeaweedFS.UseMock,
		"seaweedfs.use_fake":                  c.SeaweedFS.UseFake,
		"database_api.url":                    c.DatabaseAPI.URL,
		"kafka.brokers":                       c.Kafka.Brokers,
		"kafka.topic":                         c.Kafka.Topic,
		"kafka.producer_topic":                c.Kafka.ProducerTopic,
		"kafka.consumer_group":                c.Kafka.ConsumerGroup,
		"health.port":                         c.Health.Port,
		"health.kafka_check_timeout_seconds":  c.Health.KafkaCheckTimeout,
		"health.startup_grace_period_seconds": c.Health.StartupGracePeriod,
		"metrics.port":                        c.Metrics.Port,
	}
}
