# Image Reactor

Image metadata processor using FastAPI and asyncpg.

## Dependencies

### Development Dependencies
- **[mise](https://mise.jdx.dev/):** Used for environment management and ensuring the correct tools/versions are available.
- **[Docker](https://www.docker.com/):** Required for running the local PostgreSQL database and integration tests.

### Application Dependencies
- **[PostgreSQL](https://www.postgresql.org/):** The primary data store for the application.

## Development

### Setup

1.  **Install dependencies:**
    ```bash
    uv sync --extra dev --extra test
    ```

2.  **Environment Variables:**
    Create a `.env` file in the root directory.
    ```bash
    cp .env.example .env
    ```

3.  **Start Development Database:**
    Run the PostgreSQL container.
    ```bash
    docker compose -f dev/docker-compose.yml up -d
    ```

4.  **Run Migrations:**
    Apply the initial database schema.
    ```bash
    cd migrations
    uv run yoyo apply --batch --database ${DATABASE_URL}
    ```

    *Note: Ensure `DATABASE_URL` is set in your environment or passed explicitly.*

### Running Tests

The project uses `pytest` for testing. The test suite includes both unit and integration tests.

Run all tests:
```bash
uv run pytest
```
## Deployment

### Migrations

Database schema changes are distributed as SQL files and managed by `yoyo-migrations`.

- **Apply pending migrations:**
  ```bash
  cd migrations
  uv run yoyo apply --batch --database <DATABASE_URL>
  ```
- **List available migrations:**
  ```bash
  cd migrations
  uv run yoyo list --database <DATABASE_URL>
  ```

### Configuration

The application is configured via environment variables. Below are the key configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *Required* | PostgreSQL connection string. |
| `DB_POOL_MIN_SIZE` | `10` | Minimum size of the database connection pool. |
| `DB_POOL_MAX_SIZE` | `20` | Maximum size of the database connection pool. |
| `HOST` | `0.0.0.0` | Server host to bind to. |
| `PORT` | `8000` | Server port to listen on. |
| `LOG_LEVEL` | `INFO` | Logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL). |
| `LOG_FORMAT` | `JSON` | Format of logs (JSON or TXT). |
| `VERBOSE_API_EXCEPTIONS` | `False` | If True, returns detailed error messages in API responses. |
| `EXPOSE_METRICS` | `True` | If True, exposes Prometheus metrics at `/metrics`. |
| `DEBUG` | `False` | Enables debug mode. |
