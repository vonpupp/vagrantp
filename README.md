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
- Podman 3.0+ or Docker 20.0+ (for containers)
- Ansible 2.9+ (for provisioning, optional)

## Development

### Setting up the development environment

```bash
# Install uv (fast Python package installer)
pip install uv

# Install development dependencies
uv sync --group test --group dev

# Install custom git hooks from githooks directory first
git config core.hooksPath githooks

# Install pre-commit hooks to the custom hooks directory
uv run pre-commit install --hook-dir githooks

# Run tests
uv run pytest --cov=src tests/

# Run linting
uv run ruff check .
... individual tests ...

# Run all pre-commit at once
uv run pre-commit

```

### CI/CD

This project uses GitHub Actions for continuous integration:

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for details.

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
| `MEMORY` | RAM allocation in MB (numeric) | `2048` | `8192` |
| `CPUS` | CPU cores | `2` | `4` |
| `DISK_SIZE` | Disk size (GB) - VM only | `20G` | `50G` |
| `PROVIDER` | VM provider (required for VM) | `virtualbox` | `libvirt` |
| `BOX` | Vagrant box image - VM only | `generic/alpine319` | `ubuntu/focal64` |
| `NETWORK_MODE` | Network type (`bridge` or `default`) | `default` | `bridge` |
| `IP_ADDRESS` | Fixed IP address | Auto-assign | `192.168.1.100` |
| `PORTS` | Port forwarding rules (`host:container`) | `[]` | `8080:80,auto:443` |
| `IMAGE` | Container image - containers only | `alpine:latest` | `nginx:latest` |
| `PROVISIONING_PLAYBOOK` | Ansible playbook path | N/A | `./playbooks/site.yml` |
| `PROVISIONING_VARS` | Ansible variables file path | N/A | `./playbooks/vars.yml` |
| `PROVISIONING_AUTO_INSTALL_ANSIBLE` | Auto-install Ansible in container | `false` | `true` |
| `SSH_USER` | SSH username for VM provisioning | `root` | `ubuntu` |
| `SSH_KEY` | SSH key path for VM provisioning | Vagrant default | `~/.ssh/id_rsa` |

## Resource Units

- **Memory**: Must be specified in MB as numeric value (e.g., `2048`, `8192`)
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

## Provisioning

Vagrantp supports Ansible-based provisioning for both VMs and containers.

### How It Works

**For VMs:**

- Uses SSH connection to run Ansible playbooks
- Works with libvirt, VirtualBox, and any Vagrant provider
- Ansible can run on host machine or inside VM

**For Containers (Podman/Docker):**

- Runs Ansible playbooks inside the container via `podman exec` or `docker exec`
- Supports both Podman and Docker runtimes
- Auto-detects available runtime

**Output Format:**

- Built-in tool playbooks (bootstrap, base roles) show formatted summary output
- User-specified playbooks show raw Ansible output for easier debugging

### Auto-Installing Ansible

If your container image doesn't have Ansible pre-installed, you can use the auto-install feature:

```env
INFRA_TYPE=container
IMAGE=archlinux
PROVISIONING_PLAYBOOK=playbooks/site.yml
PROVISIONING_AUTO_INSTALL_ANSIBLE=true
```

When enabled, Vagrantp will:

1. Check if Ansible is installed in the container
2. If missing, run the bootstrap playbook (`ansible/bootstrap.yml`)
3. The bootstrap playbook detects the OS and installs Ansible appropriately:
   - **Debian/Ubuntu**: Installs via pip
   - **Arch Linux**: Installs via pacman
   - **RHEL/CentOS/Fedora**: Installs via yum/dnf
   - **Alpine**: Installs via pip
4. Then runs your main playbook

### Using Custom Bootstrap Playbook

You can provide your own bootstrap playbook by creating `<playbook-dir>/bootstrap.yml`:

```yaml
---
- name: Custom Bootstrap
  hosts: all
  become: yes
  tasks:
    - name: Install Ansible
      apt:
        name: ansible
        state: present
```

### Provisioning Options

| Option | Description |
|--------|-------------|
| `--no-provision` | Skip provisioning step entirely |
| `PROVISIONING_AUTO_INSTALL_ANSIBLE=true` | Auto-install Ansible in containers if missing |

### Example: Full Workflow with Provisioning

1. **Create .env with provisioning:**

   ```env
   INFRA_TYPE=container
   IMAGE=archlinux
   PROVISIONING_PLAYBOOK=playbooks/site.yml
   PROVISIONING_AUTO_INSTALL_ANSIBLE=true
   ```

2. **Create your playbook:**

   ```yaml
   # playbooks/site.yml
   ---
   - name: Configure infrastructure
     hosts: all
     become: yes
     tasks:
       - name: Install packages
         package:
           name:
             - git
             - vim
             - tmux
           state: present
   ```

3. **Run vagrantp up:**

   ```bash
   vagrantp up
   ```

    Output:

    ```
    ✓ Configuration validated
    → Starting infrastructure...
      INFRA_TYPE: container
      IMAGE: archlinux
    → Running Ansible provisioning...

    PLAY [Configure infrastructure] ************************************************

    TASK [Gathering Facts] *********************************************************
    ok: [default]

    TASK [Install packages] ********************************************************
    changed: [default] => (item=['git', 'vim', 'tmux'])

    PLAY RECAP *********************************************************************
    default: ok=2 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0

    ✓ Provisioning completed (15.2s)
    ```

### Skipping Reprovisioning

Vagrantp tracks provisioning state to avoid running playbooks multiple times:

```bash
vagrantp up  # First time: runs playbook
vagrantp up  # Second time: skips (already provisioned)
vagrantp rm   # Clears state
vagrantp up  # Re-runs playbook
```

To force re-provisioning, remove and recreate infrastructure:

```bash
vagrantp rm
vagrantp up
```
