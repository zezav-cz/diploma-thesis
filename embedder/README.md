# Embeder

A mock application to compute embeddings (currently image hashes) by processing messages from a Kafka topic.

## Overview

This service consumes messages from a Kafka topic, downloads images from a SeaweedFS storage, computes their SHA256 hash, and writes the result to a file. It is designed to simulate an embedding generation workload.

## Dependencies

- **Python 3.12+**
- **Kafka**: Message broker for receiving image processing tasks.
- **SeaweedFS**: Object storage for retrieving images.

## Configuration

The application is configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BROKERS` | Comma-separated list of Kafka broker addresses | **Required** |
| `SEAWEEDFS_ADDRESS` | Base address for SeaweedFS storage (e.g., `http://localhost:8080`) | **Required** |
| `KAFKA_TOPIC` | Kafka topic to consume messages from | `embeder` |
| `KAFKA_CONSUMER_GROUP` | Kafka consumer group ID | `embeder-group` |
| `OUTPUT_FILE` | Path to the output file for hashes | `image_hashes.txt` |
| `HTTP_TIMEOUT` | HTTP request timeout in seconds | `30` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, ERROR, etc.) | `INFO` |
| `LOG_FORMAT` | Log format (JSON, TXT) | `JSON` |

## Development

This project uses [mise](https://mise.jdx.dev/) for environment and task management, and [uv](https://github.com/astral-sh/uv) for dependency management.

### Prerequisites

1. Install `mise`: https://mise.jdx.dev/getting-started.html

### Setup

```bash
# Install dependencies
mise install
```

### Linting and Formatting

```bash
# Format code
mise run format

# Lint code
mise run lint
```
