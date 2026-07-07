# Image Downloader Service

This application is a specialized service designed to consume image download jobs from a Kafka topic, download the images, process them, and upload the results to a SeaweedFS storage cluster. It also reports the status of operations to a central Database API.

Key features:
- **Kafka Consumer:** Listens for image processing jobs.
- **Concurrent Workers:** Efficiently processes multiple downloads in parallel.
- **SeaweedFS Integration:** Robust storage for processed images.
- **Observability:** Built-in health checks and Prometheus metrics.

## Dependencies

The project relies on the following major components and tools:

**Infrastructure:**
- **Kafka:** For message queuing (job distribution).
- **SeaweedFS:** distributed file system for storing images.
- **Database API:** External service for reporting job status.

**Language & Tools:**
- **Go 1.24+**
- **Mise:** For managing development tools and environment.
- **Docker:** For containerization.

## Configuration

Configuration is managed via environment variables. See `.env.example` for a complete list of available options.

Key configuration sections include:

- **Logging:** Control log level (`info`, `debug`, `trace`) and format (`json`, `txt`).
- **Downloader:** settings for worker concurrency (`MAX_WORKERS`) and timeouts.
- **SeaweedFS:** Connection details for the Master and Filer URLs.
- **Kafka:** Broker addresses, topic, and consumer group settings.
- **Database API:** Endpoint for status reporting.
- **Metrics/Health:** Ports for Prometheus metrics and health check endpoints.

## Development

This project uses [mise](https://mise.jdx.dev/) to manage the development environment and tools.

1.  **Install mise:** Follow the instructions on their website.
2.  **Setup Environment:**
    ```bash
    mise install
    ```
    This will install Go, `golangci-lint`, `task`, `lefthook`, and other necessary tools defined in `mise.toml`.

3.  **Local Config:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

## Tasks

Common development tasks are defined in `mise.toml` and can be run using the `mise run` or `task` command (if installed via mise).

- **Run Application:**
  ```bash
  mise run run
  # or
  go run main.go
  ```

- **Lint Code:**
  ```bash
  mise run lint
  ```

- **Format Code:**
  ```bash
  mise run fmt
  ```

- **Update Dependencies:**
  ```bash
  mise run update-deps
  ```

- **Build & Load (Docker/Kind):**
  ```bash
  mise run build-load
  ```
