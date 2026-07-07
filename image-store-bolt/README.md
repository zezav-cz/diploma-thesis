# Image Store Bolt Project

This project uses [Puppet Bolt](https://puppet.com/docs/bolt/latest/bolt.html) to manage the deployment and configuration of an **Image Store** based on **SeaweedFS**.

## Features

- **SeaweedFS Master Deployment**: Plan to deploy and configure SeaweedFS master servers.
- **SeaweedFS Volume Deployment**: Plan to deploy and configure SeaweedFS volume servers.
- **Infrastructure Management**: Includes an inventory setup for managing Master and Volume nodes with specific facts (`dc`, `rack_name`, `disk`).

## Dependencies

- **[mise](https://mise.jdx.dev/)**: Manages project tools (Ruby, etc.).
- **Ruby**: ~3.2
- **Puppet Bolt**: ~4.0

## Setup

1. **Install tools and trust the config**:
   ```bash
   mise trust
   mise install
   ```

2. **Install Ruby gems**:
   ```bash
   bundle install
   ```

3. **Install Bolt modules**:
   ```bash
   bundle exec bolt module install
   ```

4. **Configure Inventory**:
   Edit `inventory.yaml` to add your hosts:
   ```bash
   vim inventory.yaml
   ```

## Usage

### Check Connections
```bash
bundle exec bolt plan run image_store::ping -t all
```

### Deploy Master
```bash
bundle exec bolt plan run image_store::master --targets master
```

### Deploy Volume
```bash
bundle exec bolt plan run image_store::volume masters='["master-host:9333"]' --targets volume
```

### Development Tasks

This project uses `mise` tasks for development.

- **Lint code**:
  ```bash
  mise run lint
  ```
- **Fix code style**:
  ```bash
  mise run fix
  ```

## Reference

### Ports
SeaweedFS ports are organized as follows `70XX`:

| Service | Port Range |
|---------|------------|
| Master  | 701X       |
| Filer   | 702X       |
| Admin   | 703X       |
| Volume  | 704X       |

Offsets:
- `http`: +0
- `metrics`: +1
- `public`: +5
- `grpc`: +1000
