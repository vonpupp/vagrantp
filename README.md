# Vagrantp

Template-driven infrastructure system for creating and managing VMs and Podman containers from simple `.env` configuration files.

## Features

- **Template-Driven**: No need to write individual Vagrantfiles - just create a `.env` file
- **Multi-Platform**: Support for both VMs (Vagrant) and containers (Podman)
- **Simple CLI**: Single command interface with `up`, `ssh`, `stop`, and `rm` commands
- **Resource Configuration**: Customize RAM, CPU, disk size, networking, and port forwarding
- **Idempotent Operations**: Safe to run commands multiple times

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vagrantp.git
cd vagrantp

# Install in development mode
pip install -e .
```

## Requirements

- Python 3.11+
- Vagrant 2.3+ (for VMs)
- VirtualBox or libvirt (for VMs)
- Podman 3.0+ (for containers)
- Ansible 2.9+ (for provisioning, optional)

## Development

### Setting up the development environment

```bash
# Install uv (fast Python package installer)
pip install uv

# Install development dependencies
uv sync --group test --group dev

# Run tests
uv run pytest tests/

# Run linting
uv run ruff check .
uv run ruff format .
uv run pyrefly check src/
uv run deadcode src/

# Run tests with coverage
uv run pytest --cov=src tests/
```

### CI/CD

This project uses GitHub Actions for continuous integration:

- **Testing**: Runs on Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14
- **Linting**: Uses Ruff for code style and formatting, Pyrefly for type checking
- **Coverage**: Generates code coverage reports with pytest-cov

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for details.

### Code Quality Tools

- **Ruff**: Fast Python linter and formatter
- **Pyrefly**: Type checker (alternative to mypy)
- **Deadcode**: Dead code detector
- **pytest**: Testing framework with coverage support

## Quick Start

### VM Example

1. **Create a project directory:**

```bash
mkdir ~/myvm-project
cd ~/myvm-project
```

2. **Create a `.env` file:**

```env
# Infrastructure type: vm or container
INFRA_TYPE=vm

# VM provider: virtualbox or libvirt (required for VM)
PROVIDER=libvirt

# Resources (optional, defaults shown)
MEMORY=2048
CPUS=2
DISK_SIZE=20G

# Networking (optional)
NETWORK_MODE=bridge
IP_ADDRESS=192.168.1.100

# Port forwarding (optional)
PORTS=8080:80
```

3. **Create and start infrastructure:**

```bash
vagrantp up
```

4. **Connect to infrastructure:**

```bash
vagrantp ssh
```

5. **Stop infrastructure:**

```bash
vagrantp stop
```

6. **Remove infrastructure:**

```bash
vagrantp rm
```

### Container Example

1. **Create a project directory:**

```bash
mkdir ~/mycontainer-project
cd ~/mycontainer-project
```

2. **Create a `.env` file:**

```env
# Infrastructure type: container
INFRA_TYPE=container

# Resources (optional, defaults shown)
MEMORY=512
CPUS=1

# Image (optional, default: alpine:latest)
IMAGE=alpine:latest

# Networking (optional)
NETWORK_MODE=bridge

# Port forwarding (optional)
PORTS=8080:80,auto:443
```

3. **Create and start infrastructure:**

```bash
vagrantp up
```

## CLI Commands

### `vagrantp up [--dry-run] [--no-provision]`

Create and start infrastructure from `.env` configuration.

- `--dry-run`: Validate configuration without creating infrastructure
- `--no-provision`: Skip provisioning step

### `vagrantp ssh [--command COMMAND]`

Connect to infrastructure via SSH.

- `--command COMMAND`: Execute single command and exit

### `vagrantp stop [--force]`

Stop infrastructure gracefully.

- `--force`: Force stop without graceful shutdown

### `vagrantp rm [--force]`

Remove infrastructure and all resources.

- `--force`: Force removal without confirmation prompt

### `vagrantp --help`

Show help message for all commands.

### `vagrantp --version`

Show version information.

## Configuration Reference

### Required Fields

| Field | Description | Example |
|--------|-------------|---------|
| `INFRA_TYPE` | Infrastructure type (`vm` or `container`) | `vm` |

### Optional Fields

| Field | Description | Default | Example |
|--------|-------------|---------|---------|
| `INFRA_ID` | Custom infrastructure ID | Project directory name | `myapp-dev` |
| `MEMORY` | RAM allocation (MB or GB) | `2048` (2GB) | `8192` |
| `CPUS` | CPU cores | `2` | `4` |
| `DISK_SIZE` | Disk size (GB) - VM only | `20G` | `50G` |
| `PROVIDER` | VM provider (required for VM) | `virtualbox` | `libvirt` |
| `BOX` | Vagrant box image - VM only | `generic/alpine319` | `ubuntu/focal64` |
| `NETWORK_MODE` | Network type (`bridge` or `default`) | `default` | `bridge` |
| `IP_ADDRESS` | Fixed IP address | Auto-assign | `192.168.1.100` |
| `PORTS` | Port forwarding rules (`host:container`) | `[]` | `8080:80,auto:443` |
| `IMAGE` | Container image - containers only | `alpine:latest` | `nginx:latest` |
| `PROVISIONING_PLAYBOOK` | Ansible playbook path | N/A | `./playbooks/site.yml` |

## Resource Units

- **Memory**: Can be specified in MB (e.g., `2048`) or GB (e.g., `2G`, `2GB`)
- **CPU**: Integer number of cores (e.g., `1`, `2`, `4`)
- **Disk**: Can be specified in GB (e.g., `20G`, `20GB`) or MB (e.g., `20000M`, `20000MB`)

## Networking

### Port Forwarding

Port mappings are specified as `host_port:container_port`, separated by commas.

```env
PORTS=8080:80,8081:443,auto:8082
```

- `8080:80`: Forward host port 8080 to container port 80
- `8081:443`: Forward host port 8081 to container port 443
- `auto:8082`: Auto-assign a host port to container port 8082

### Network Modes

- **default**: Use default NAT/networking
- **bridge**: Use bridged networking for direct network access

## Troubleshooting

### Infrastructure Already Exists

```
✗ Infrastructure 'myproject' already exists (state: running)
  → Run 'vagrantp ssh' to connect, or 'vagrantp stop' then 'vagrantp rm' to recreate
```

### Configuration Not Found

```
✗ Configuration file .env not found in current directory
  → Create a .env file with required INFRA_TYPE field
```

### Invalid Configuration

```
✗ Invalid value for MEMORY: must be ≥ 512MB, got: 256
  → Check MEMORY field in .env file
```

## Documentation

For detailed documentation, examples, and troubleshooting, see:

- `specs/001-template-driven-infra/quickstart.md` - Detailed quick start guide
- `specs/001-template-driven-infra/contracts/cli-api.md` - CLI API specification
- `specs/001-template-driven-infra/data-model.md` - Data model and entities

## License

MIT
