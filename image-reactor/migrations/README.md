# Database Migrations

Postgres migrations are handled via [yoyo-migrations](https://ollycope.com/software/yoyo/latest/).

## Commands

- **Check status:**
  ```bash
  uv run yoyo list --database=<DATABASE_URL>
  ```

- **Apply pending migrations:**
  ```bash
  uv run yoyo apply --batch --database=<DATABASE_URL>
  ```

- **Rollback last migration:**
  ```bash
  uv run yoyo rollback --database=<DATABASE_URL>
  ```

- **Create a new migration:**
  ```bash
  uv run yoyo new migrations --sql -m "migration_name"
  ```
