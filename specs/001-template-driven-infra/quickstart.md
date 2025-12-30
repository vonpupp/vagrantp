# Quick Start Guide: Vagrantp

**Feature**: Template-Driven Infrastructure (001-template-driven-infra)
**Version**: 1.0.0
**Date**: 2025-12-29

## Overview

Vagrantp is a template-driven infrastructure tool that allows you to create and manage VMs and Podman containers from simple `.env` configuration files. No need to write individual Vagrantfiles for each project!

---

## Prerequisites

### Required Software

1. **Python 3.11+**: Install from your distribution's package manager

   ```bash
   # Arch Linux
   sudo pacman -S python

   # Ubuntu/Debian
   sudo apt install python3.11
   ```

2. **Vagrant**: Required for VM infrastructure

   ```bash
   # Arch Linux
   sudo pacman -S vagrant

   # Ubuntu/Debian
   # Download from https://developer.hashicorp.com/vagrant/downloads
   ```

3. **Virtualization Provider**: Choose one or both:
   - **VirtualBox** (default): `sudo pacman -S virtualbox` (Arch)
   - **libvirt** (recommended): `sudo pacman -S libvirt qemu vagrant-libvirt`

4. **Podman**: Required for container infrastructure

   ```bash
   # Arch Linux
   sudo pacman -S podman

   # Ubuntu/Debian
   sudo apt install podman
   ```

5. **Ansible**: Required for provisioning

   ```bash
   sudo pacman -S ansible
   ```

### Verify Installation

```bash
python --version      # Should be 3.11 or higher
vagrant --version     # Should be 2.3 or higher
virtualbox --version  # Or virsh --version for libvirt
podman --version      # Should be 3.0 or higher
ansible --version     # Should be 2.9 or higher
```

---

## Installation

### Install Vagrantp

```bash
# Clone the repository
git clone https://github.com/yourusername/vagrantp.git
cd vagrantp

# Install in development mode
pip install -e .
```

### Verify Installation

```bash
vagrantp --help
```

You should see the help message listing available commands: `up`, `ssh`, `stop`, `rm`.

---

## Your First Project

### Step 1: Create a Project Directory

```bash
mkdir ~/myproject
cd ~/myproject
```

### Step 2: Create a Configuration File

Create a `.env` file in your project directory:

```env
# .env file for myproject

# Infrastructure type: vm or container
INFRA_TYPE=vm

# VM provider: virtualbox or libvirt (required for VM)
PROVIDER=libvirt

# Resources (optional, with defaults shown)
MEMORY=2048
CPUS=2
DISK_SIZE=20G

# Networking (optional)
NETWORK_MODE=bridge
IP_ADDRESS=192.168.1.100

# Port forwarding (optional)
# Format: host_port:container_port
PORTS=8080:80

# Provisioning (optional)
# Uncomment to enable Ansible provisioning
# PROVISIONING_PLAYBOOK=./playbooks/site.yml

# SSH access (optional)
# SSH_USER=root
# SSH_KEY=/home/youruser/.ssh/id_rsa
```

### Step 3: Start Infrastructure

```bash
vagrantp up
```

You should see progress indicators:

```
✓ Configuration validated
→ Starting infrastructure...
⠹ Creating VM [██████████████████] 100% (2m15s)
⠹ Booting VM... [DONE]
✓ Infrastructure is ready
  ID: myproject
  Type: VM
  State: running
  IP: 192.168.1.100

Next steps:
  → Run 'vagrantp ssh' to connect
```

### Step 4: Connect to Infrastructure

```bash
vagrantp ssh
```

You're now connected to your VM!

### Step 5: Stop Infrastructure

```bash
vagrantp stop
```

Output:

```
⠹ Sending shutdown signal...
⠹ Waiting for graceful shutdown [████████████████] 100% (12s)
✓ Infrastructure stopped
```

### Step 6: Remove Infrastructure

```bash
vagrantp rm
```

You'll be prompted to confirm:

```
⚠ Warning: This will permanently remove infrastructure 'myproject'
→ Type 'yes' to confirm: yes
⠹ Cleaning up resources...
✓ Infrastructure removed (23s)
```

---

## Container Example

Want to use containers instead of VMs? Just change the `.env` file:

```env
# .env file for container project

# Infrastructure type: container
INFRA_TYPE=container

# Resources (optional, with defaults shown)
MEMORY=512
CPUS=1

# Networking (optional)
NETWORK_MODE=bridge

# Port forwarding (optional)
PORTS=8080:80,auto:443

# Image to use (optional)
IMAGE=alpine:latest
```

Run the same commands:

```bash
vagrantp up
vagrantp ssh
vagrantp stop
vagrantp rm
```

---

## Provisioning with Ansible

### Step 1: Create an Ansible Playbook

Create `playbooks/site.yml`:

```yaml
---
- name: Configure infrastructure
  hosts: all
  become: yes

  tasks:
    - name: Install Nginx
      package:
        name: nginx
        state: present

    - name: Start Nginx
      service:
        name: nginx
        state: started
        enabled: yes

    - name: Create web directory
      file:
        path: /var/www/html
        state: directory
        owner: www-data
        group: www-data
```

### Step 2: Update .env File

Add the provisioning playbook (and optional variables file):

```env
INFRA_TYPE=vm
PROVIDER=libvirt
MEMORY=2048
CPUS=2

# Enable provisioning
PROVISIONING_PLAYBOOK=./playbooks/site.yml
# Optional: variables file
PROVISIONING_VARS=./playbooks/vars.yml
```

**Note**: Vagrantp includes a default playbook at `ansible/site.yml` that installs base packages. Use it directly or copy it as a template.

### Step 3: Start Infrastructure

```bash
vagrantp up
```

The provisioning playbook will run automatically after the infrastructure boots:

```
✓ Infrastructure is ready
⠹ Running Ansible provisioning [████████████████] 100% (30s)
   - Installing Nginx... [DONE]
   - Starting Nginx... [DONE]
   - Creating web directory... [DONE]
✓ Provisioning completed
```

---

## Multiple Projects

You can manage multiple projects independently:

```bash
# Project 1
cd ~/projects/api-service
vagrantp up  # Creates infrastructure for api-service

# Project 2
cd ~/projects/web-app
vagrantp up  # Creates infrastructure for web-app

# Both projects run independently!
```

Each project has its own `.env` file and infrastructure.

---

## Common Workflows

### Development Workflow

```bash
# Start infrastructure for development
cd ~/myproject
vagrantp up

# Connect and work
vagrantp ssh

# Stop when done (keeps data)
vagrantp stop

# Resume later
vagrantp up  # Infrastructure restarts with data preserved
```

### Clean Workflow

```bash
# Start fresh
cd ~/myproject
vagrantp up

# Work...

# Completely remove when done
vagrantp rm  # Removes all data
```

### Force Operations

```bash
# Force stop without graceful shutdown
vagrantp stop --force

# Force remove without stopping first
vagrantp rm --force
```

---

## Configuration Reference

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `INFRA_TYPE` | Infrastructure type (`vm` or `container`) | `vm` |

### Optional Fields

| Field | Description | Default | Example |
|-------|-------------|---------|---------|
| `INFRA_ID` | Custom infrastructure ID | Project directory name | `myapp-dev` |
| `MEMORY` | RAM allocation | `2048` (2GB) | `8192` |
| `CPUS` | CPU cores | `2` | `4` |
| `DISK_SIZE` | Disk size | `20G` | `50G` |
| `PROVIDER` | VM provider (required for VM) | `virtualbox` | `libvirt` |
| `NETWORK_MODE` | Network type | `default` | `bridge` |
| `IP_ADDRESS` | Fixed IP address | Auto-assign | `192.168.1.100` |
| `PORTS` | Port forwarding | `[]` | `8080:80,auto:443` |
| `PROVISIONING_PLAYBOOK` | Ansible playbook path | N/A | `./playbooks/site.yml` |
| `SSH_USER` | SSH username | System default | `av` |
| `SSH_KEY` | SSH private key path | System default | `/home/av/.ssh/id_rsa` |

---

## Troubleshooting

### Configuration Errors

**Error**: `Configuration file .env not found in current directory`

**Solution**: Create a `.env` file in your project directory with the required `INFRA_TYPE` field.

**Error**: `Invalid value for MEMORY: must be ≥ 512MB, got: 256`

**Solution**: Update `MEMORY` in `.env` to a valid value (e.g., `MEMORY=2048`).

### Infrastructure Errors

**Error**: `Infrastructure 'myproject' already exists (state: running)`

**Solution**: Infrastructure is already running. Run `vagrantp ssh` to connect, or `vagrantp stop` followed by `vagrantp rm` to recreate.

**Error**: `Insufficient RAM: need 8192MB, 6000MB available`

**Solution**: Stop other running projects, or reduce `MEMORY` in `.env` file.

**Error**: `Port 8080 is already in use by project 'other-project'`

**Solution**: Use a different port in your `.env` file (e.g., `PORTS=8081:80`), or stop the other project.

### Provider Errors

**Error**: `Provider 'libvirt' is not installed or not configured`

**Solution**: Install the provider:

```bash
# Arch Linux
sudo pacman -S libvirt qemu vagrant-libvirt

# Enable and start libvirtd
sudo systemctl enable --now libvirtd

# Add user to libvirt group
sudo usermod -a -G libvirt $(whoami)
# Log out and back in
```

### SSH Connection Errors

**Error**: `Failed to establish SSH connection: Connection timeout after 30 seconds`

**Solution**:

1. Verify infrastructure is running: `vagrantp status`
2. Check network connectivity to the IP address
3. Verify SSH service is running in the infrastructure
4. Check firewall rules on host system

### Provisioning Errors

**Error**: `Ansible playbook failed: task 'Install Nginx' returned non-zero exit code 1`

**Solution**:

1. Check playbook syntax: `ansible-playbook --syntax-check playbooks/site.yml`
2. Review playbook for errors
3. Test playbook manually: `ansible-playbook playbooks/site.yml -i inventory.ini`

---

## Advanced Usage

### Dynamic Port Allocation

Don't want to manage port conflicts? Use automatic port assignment:

```env
PORTS=auto:80,auto:443
```

Vagrantp will automatically assign available ports from a managed pool (e.g., 8100-8900).

### Fixed IP Assignment

Assign a fixed IP for predictable networking:

```env
NETWORK_MODE=bridge
IP_ADDRESS=192.168.1.100
```

### SSH Key Configuration

Use a specific SSH key:

```env
SSH_USER=av
SSH_KEY=/home/av/.ssh/myproject_key
```

### Dry Run

Validate configuration without creating infrastructure:

```bash
vagrantp up --dry-run
```

### Skip Provisioning

Create infrastructure without running provisioning:

```bash
vagrantp up --no-provision
```

### Execute Single Command

Run a single command via SSH without interactive shell:

```bash
vagrantp ssh --command "cat /etc/os-release"
```

---

## Getting Help

- **View command help**: `vagrantp --help` or `vagrantp <command> --help`
- **Check version**: `vagrantp --version`
- **Report issues**: <https://github.com/yourusername/vagrantp/issues>
- **Documentation**: <https://github.com/yourusername/vagrantp/wiki>

---

## Next Steps

- Read the full [Data Model](data-model.md) for detailed entity definitions
- Review the [CLI API Contract](contracts/cli-api.md) for API specifications
- Explore [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- Check out [Vagrant Documentation](https://www.vagrantup.com/docs) for advanced provider configuration
- Explore [Podman Documentation](https://docs.podman.io/) for container-specific features

---

**Happy provisioning! 🚀**
