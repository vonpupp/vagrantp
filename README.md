# Vagrantp

Template-driven infrastructure system for creating and managing VMs and Podman containers from simple `.env` configuration files.

## Features

- **Template-Driven**: No need to write individual Vagrantfiles - just create a `.env` file
- **Multi-Platform**: Support for both VMs (Vagrant) and containers (Podman)
- **Simple CLI**: Single command interface with `up`, `ssh`, `stop`, and `rm` commands
- **Resource Configuration**: Customize RAM, CPU, disk size, networking, and port forwarding
- **Automated Provisioning**: Ansible playbook integration for automated configuration
- **Idempotent Operations**: Safe to run commands multiple times

## Installation

```bash
# Install in development mode
pip install -e .
```

## Quick Start

### 1. Create a Project Directory

```bash
mkdir ~/myproject
cd ~/myproject
```

### 2. Create a Configuration File

Create a `.env` file:

```env
# Infrastructure type: vm or container
INFRA_TYPE=vm

# VM provider: virtualbox or libvirt (required for VM)
PROVIDER=libvirt

# Resources (optional)
MEMORY=2048
CPUS=2
DISK_SIZE=20G

# Networking (optional)
NETWORK_MODE=bridge
IP_ADDRESS=192.168.1.100
```

### 3. Start Infrastructure

```bash
vagrantp up
```

### 4. Connect to Infrastructure

```bash
vagrantp ssh
```

### 5. Stop Infrastructure

```bash
vagrantp stop
```

### 6. Remove Infrastructure

```bash
vagrantp rm
```

## Requirements

- Python 3.11+
- Vagrant 2.3+
- VirtualBox or libvirt (for VMs)
- Podman 3.0+ (for containers)
- Ansible 2.9+ (for provisioning)

## Documentation

See `specs/001-template-driven-infra/quickstart.md` for detailed documentation and examples.

## License

MIT
