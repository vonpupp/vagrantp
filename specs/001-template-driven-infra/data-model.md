# Data Model: Template-Driven Infrastructure

**Feature**: Template-Driven Infrastructure (001-template-driven-infra)
**Date**: 2025-12-29
**Phase**: Phase 1 - Design

## Overview

This document defines the core data entities for the template-driven infrastructure system. The system manages project directories, infrastructure instances (VMs and containers), configuration files, and provisioning scripts through a unified CLI wrapper interface.

---

## Core Entities

### 1. Project Directory

**Description**: A folder containing a configuration file that defines infrastructure requirements. The directory name serves as the default infrastructure identifier.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `name` | string | Yes | Directory name (basename of path) | Must be valid hostname (a-z, 0-9, hyphen) |
| `path` | string | Yes | Absolute path to project directory | Must exist and be readable |
| `config_file` | string | Yes | Path to configuration file (`.env` or custom) | Must exist if specified |
| `infrastructure_id` | string | No | Custom infrastructure identifier (optional) | Defaults to `name` if not specified |

**Relationships**:

- `has_one` Configuration File
- `has_many` Infrastructure Instances (one per infra_type)

**State Transitions**:

- N/A (project directories are static, managed by user)

**Validation Rules**:

- Path must be absolute
- Directory must be readable
- Configuration file must exist and be valid YAML/.env format

---

### 2. Infrastructure Instance

**Description**: A running virtual machine or container created from a project directory's configuration. Each instance has unique resources, networking, and state.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | string | Yes | Unique infrastructure identifier | Must be unique on host system |
| `infra_type` | enum | Yes | Type of infrastructure (`vm` or `container`) | Must be one of: `vm`, `container` |
| `state` | enum | Yes | Current state of infrastructure | One of: `not_created`, `creating`, `running`, `stopped`, `removing` |
| `project_path` | string | Yes | Path to project directory | Must be absolute |
| `provider` | string | Yes | Backend provider (`virtualbox`, `libvirt`, `podman`) | Must match infra_type (VM providers for vm, podman for container) |
| `resources` | object | Yes | Allocated resources | See Resources object |
| `networking` | object | Yes | Network configuration | See Networking object |
| `provisioning` | object | No | Provisioning configuration | See Provisioning object |
| `created_at` | datetime | Yes | Timestamp when instance was created | Auto-generated |
| `updated_at` | datetime | Yes | Timestamp when instance was last modified | Auto-updated |

**State Machine**:

```
not_created ──(up)──> creating ──(boot_complete)──> running
     │                                             │
     │                                            (stop)
     │                                             │
     └──────────────────────────<──────────────────┘
                          │
                    (rm/clean)
                          │
                          v
                    removing ──(cleanup_complete)──> not_created
```

**State Transitions**:

- `not_created` → `creating`: When `up` command is executed
- `creating` → `running`: When infrastructure boots successfully
- `running` → `stopped`: When `stop` command is executed
- `stopped` → `running`: When `up` command is executed on stopped infrastructure
- `stopped` → `removing`: When `rm` command is executed
- `running` → `removing`: When `rm` command is executed (force stop + remove)
- `removing` → `not_created`: When cleanup completes

**Validation Rules**:

- `id` must be unique across all instances on host
- `infra_type` and `provider` must be compatible (VM providers for vm, podman for container)
- `resources` must not exceed host system limits
- `networking` must have no port conflicts with other instances
- State transitions must follow state machine rules

**Operations**:

- `create()`: Create infrastructure (up command)
- `connect()`: Establish SSH connection (ssh command)
- `stop()`: Stop infrastructure gracefully (stop command)
- `remove()`: Remove infrastructure and all resources (rm command)
- `status()`: Get current state and metadata (internal use)

---

### 3. Configuration File

**Description**: A file in the project directory containing key-value pairs that specify infrastructure type, resources, networking, and provisioning settings.

**Fields** (parsed from .env file):

| Field | Type | Required | Description | Default | Validation |
|-------|------|----------|-------------|---------|------------|
| `INFRA_TYPE` | enum | Yes | Infrastructure type | N/A | Must be `vm` or `container` |
| `INFRA_ID` | string | No | Custom infrastructure identifier | Project directory name | Must be valid hostname |
| `MEMORY` | string | No | RAM allocation | `2048` | Must be integer ≥ 512, format: `<bytes>` or `<unit>` (e.g., `2G`) |
| `CPUS` | integer | No | CPU cores | `2` | Must be integer ≥ 1 |
| `DISK_SIZE` | string | No | Disk size | `20G` | Must be valid size format (e.g., `20G`, `50000M`) |
| `PROVIDER` | string | No | VM provider (if VM) | `virtualbox` | Must be installed on host |
| `NETWORK_MODE` | enum | No | Network type | `default` | Must be `bridge` or `default` |
| `IP_ADDRESS` | string | No | Fixed IP address (optional) | Auto-assign | Must be valid IPv4 address if provided |
| `PORTS` | list | No | Port forwarding rules | `[]` | Format: `host:container` or `auto:container` |
| `PROVISIONING_PLAYBOOK` | string | No | Path to Ansible playbook | N/A | Must exist if specified |
| `SSH_USER` | string | No | SSH username | `root` or system default | N/A |
| `SSH_KEY` | string | No | Path to SSH private key | Auto-generated or default | Must exist if specified |

**Example Configuration**:

```env
# Infrastructure type (required)
INFRA_TYPE=vm

# Resources (optional, defaults shown)
MEMORY=8192
CPUS=4
DISK_SIZE=50G

# VM provider (required for VM)
PROVIDER=libvirt

# Networking (optional)
NETWORK_MODE=bridge
IP_ADDRESS=192.168.1.100
PORTS=8080:80,auto:443

# Provisioning (optional)
PROVISIONING_PLAYBOOK=./playbooks/site.yml

# SSH access (optional)
SSH_USER=av
SSH_KEY=/home/av/.ssh/id_rsa
```

**Validation Rules**:

- `INFRA_TYPE` is required
- If `INFRA_TYPE=vm`, `PROVIDER` is required
- `MEMORY` must be ≥ 512MB
- `CPUS` must be ≥ 1
- `DISK_SIZE` must be ≥ 5GB
- `IP_ADDRESS` must be in valid range for network mode
- `PORTS` must not conflict with other instances
- `PROVISIONING_PLAYBOOK` must exist if specified
- `SSH_KEY` must exist if specified

**Data Validation**:

```python
def validate_config(config: dict) -> ValidationResult:
    # Check required fields
    if "INFRA_TYPE" not in config:
        raise ValidationError("INFRA_TYPE is required")

    # Validate INFRA_TYPE
    if config["INFRA_TYPE"] not in ["vm", "container"]:
        raise ValidationError("INFRA_TYPE must be 'vm' or 'container'")

    # Validate provider for VM
    if config["INFRA_TYPE"] == "vm" and "PROVIDER" not in config:
        raise ValidationError("PROVIDER is required for VM infrastructure")

    # Validate resource constraints
    memory = parse_memory(config.get("MEMORY", "2048"))
    if memory < 512:
        raise ValidationError("MEMORY must be at least 512MB")

    cpus = int(config.get("CPUS", "2"))
    if cpus < 1:
        raise ValidationError("CPUS must be at least 1")

    # Validate networking
    if "IP_ADDRESS" in config:
        if not is_valid_ipv4(config["IP_ADDRESS"]):
            raise ValidationError("Invalid IP_ADDRESS format")

    # Validate port conflicts
    if "PORTS" in config:
        for port_mapping in parse_ports(config["PORTS"]):
            if port_conflicts(port_mapping):
                raise ValidationError(
                    f"Port {port_mapping.host_port} is already in use"
                )

    # Validate provisioning
    if "PROVISIONING_PLAYBOOK" in config:
        if not os.path.exists(config["PROVISIONING_PLAYBOOK"]):
            raise ValidationError(
                f"PROVISIONING_PLAYBOOK does not exist: {config['PROVISIONING_PLAYBOOK']}"
            )

    return ValidationResult(valid=True)
```

---

### 4. Wrapper Command

**Description**: A command-line interface that provides up, ssh, stop, and rm subcommands for infrastructure management.

**Commands**:

| Command | Purpose | Parameters | Behavior |
|---------|---------|------------|----------|
| `up` | Create and start infrastructure | None | Read .env, validate config, create infra, run provisioning |
| `ssh` | Connect to infrastructure | None | Establish SSH connection using configured credentials |
| `stop` | Stop infrastructure | `--force` | Stop infrastructure gracefully or forcefully |
| `rm` | Remove infrastructure | `--force` | Remove infrastructure and all resources |

**Command Signatures**:

```bash
# Create and start infrastructure
vagrantp up

# Connect to infrastructure
vagrantp ssh

# Stop infrastructure
vagrantp stop [--force]

# Remove infrastructure
vagrantp rm [--force]
```

**Error Handling**:

- Missing .env file: Clear error with instructions to create configuration
- Invalid configuration: Show specific validation errors with line numbers
- Infrastructure already exists: Show current state, suggest `vagrantp ssh` or `vagrantp stop`
- Insufficient resources: Show resource requirements vs available resources
- Port conflicts: Show conflicting ports and which project is using them
- Provider not available: Show missing provider and installation instructions
- SSH connection failed: Show possible causes and troubleshooting steps

**Exit Codes**:

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Infrastructure already exists
- `4`: Insufficient resources
- `5`: Provider not available
- `6`: Port conflict
- `7`: Provisioning failed

**User Feedback**:

- Print initial status message in < 100ms
- Show progress for operations > 10 seconds
- Display step-by-step progress for multi-stage operations
- Provide ETA when possible for long-running operations
- Show clear success/completion messages
- Display helpful error messages with actionable guidance

---

### 5. Provisioning Script

**Description**: An automated configuration script specified in the configuration file that runs automatically after infrastructure creation to install and configure software.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `type` | enum | Yes | Provisioning type | Must be `ansible` (constitution requirement) |
| `path` | string | Yes | Path to playbook or script | Must exist and be readable |
| `playbook_name` | string | Yes | Name of Ansible playbook | Must be valid filename |
| `variables_file` | string | No | Path to variables file | Must exist if specified |
| `extra_vars` | dict | No | Extra variables to pass | N/A |
| `dry_run` | boolean | No | Run in dry-run mode | Default: `false` |

**Supported Types**:

- **Ansible Playbook**: Primary provisioning method (constitution requirement)
  - Must be idempotent
  - Must support dry-run mode
  - Must be testable in isolation
  - Secrets must use environment variables (never hardcoded)

**Execution Flow**:

1. Infrastructure boots successfully
2. Verify SSH connection is established
3. Execute provisioning script
4. Capture output and exit code
5. On failure: Show error details and suggest troubleshooting
6. On success: Display completion message

**Example Provisioning Configuration**:

```env
# Provisioning with Ansible
PROVISIONING_PLAYBOOK=./playbooks/site.yml
PROVISIONING_VARS=./playbooks/vars.yml
```

**Validation Rules**:

- Playbook must exist
- Playbook must be valid YAML
- Playbook must be idempotent (testable)
- Playbook must be executable from host system
- Variables file must exist if specified

---

## Supporting Objects

### Resources Object

**Description**: Resource allocation for infrastructure instance.

**Fields**:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `memory_mb` | integer | Yes | RAM allocation in MB | ≥ 512 |
| `cpus` | integer | Yes | CPU cores | ≥ 1 |
| `disk_gb` | integer | Yes | Disk size in GB | ≥ 5 |

**Validation**:

- Must not exceed host system limits
- Must be compatible with provider constraints

---

### Networking Object

**Description**: Network configuration for infrastructure instance.

**Fields**:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `mode` | enum | Yes | Network mode | `bridge` or `default` |
| `ip_address` | string | No | Fixed IP address | Valid IPv4 if specified |
| `ports` | list | No | Port forwarding rules | No conflicts |

**Port Mapping Structure**:

```python
{
    "host_port": int,  # Port on host (0 for auto)
    "container_port": int,  # Port in infrastructure
    "protocol": str,  # "tcp" or "udp"
    "auto": bool,  # True if host_port should be auto-assigned
}
```

**Validation**:

- Must be compatible with provider
- No port conflicts across instances
- IP address must be in valid range for network mode

---

### Provisioning Object

**Description**: Provisioning configuration for infrastructure instance.

**Fields**:

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `type` | string | Yes | Provisioning type | Must be `ansible` |
| `playbook_path` | string | Yes | Path to Ansible playbook | Must exist |
| `variables_path` | string | No | Path to variables file | Must exist if specified |
| `extra_vars` | dict | No | Extra Ansible variables | N/A |
| `dry_run` | boolean | No | Dry-run mode flag | Default: `false` |

---

## Entity Relationships

```
┌─────────────────┐
│ Project Directory│
│ (name, path)     │
└────────┬────────┘
         │
         │ has_one
         ▼
┌──────────────────┐
│ Configuration    │
│ File (.env)      │
└────────┬─────────┘
         │
         │ defines
         ▼
┌────────────────────┐
│ Infrastructure    │
│ Instance           │
│ (id, infra_type,  │
│  state, resources,│
│  networking)      │
└─────────┬──────────┘
          │
          │ managed_by
          ▼
┌────────────────────┐
│ Wrapper Command    │
│ (up, ssh, stop, rm)│
└────────────────────┘

Infrastructure Instance ───> Provisioning Script
```

---

## Data Flow

### `up` Command Flow

1. **User executes**: `vagrantp up`
2. **Read .env**: Parse configuration file from current directory
3. **Validate configuration**: Check required fields, constraints, port conflicts
4. **Check existing state**: Verify infrastructure doesn't already exist
5. **Generate infrastructure definition**: Create Vagrantfile or Podman spec from template
6. **Create infrastructure**: Delegate to Vagrant or Podman
7. **Wait for boot**: Monitor boot progress with feedback
8. **Run provisioning**: Execute Ansible playbook if specified
9. **Report status**: Display completion message and next steps

### `ssh` Command Flow

1. **User executes**: `vagrantp ssh`
2. **Read .env**: Parse configuration file
3. **Validate configuration**: Check infrastructure exists and is running
4. **Get connection details**: Retrieve IP, user, SSH key from configuration
5. **Establish SSH connection**: Use subprocess to invoke SSH client
6. **Hand over control**: Attach user terminal to SSH session

### `stop` Command Flow

1. **User executes**: `vagrantp stop`
2. **Read .env**: Parse configuration file
3. **Validate configuration**: Check infrastructure exists and is running
4. **Stop infrastructure**: Delegate to Vagrant or Podman
5. **Wait for shutdown**: Monitor shutdown progress
6. **Report status**: Display completion message

### `rm` Command Flow

1. **User executes**: `vagrantp rm [--force]`
2. **Read .env**: Parse configuration file
3. **Validate configuration**: Check infrastructure exists
4. **Stop if running**: Stop infrastructure if running (unless --force)
5. **Remove resources**: Delegate to Vagrant or Podman for cleanup
6. **Wait for cleanup**: Monitor removal progress
7. **Report status**: Display completion message

---

## Error Handling

### Error Categories

1. **Configuration Errors**:
   - Missing .env file
   - Invalid .env syntax
   - Missing required fields
   - Invalid field values
   - Resource constraint violations
   - Port conflicts

2. **Infrastructure Errors**:
   - Provider not available
   - Insufficient host resources
   - Infrastructure creation failure
   - Boot failure
   - Network configuration failure

3. **Provisioning Errors**:
   - Playbook not found
   - Invalid playbook syntax
   - Playbook execution failure
   - SSH connection failure during provisioning

4. **State Errors**:
   - Infrastructure already exists
   - Infrastructure not found
   - Invalid state transition
   - Concurrent modification

### Error Response Format

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string",
    "suggestion": "string"
  }
}
```

### Error Codes Mapping

| Error Code | Exit Code | Example Message |
|------------|-----------|-----------------|
| `CONFIG_MISSING` | 2 | "Configuration file .env not found in current directory" |
| `CONFIG_INVALID` | 2 | "Invalid value for MEMORY: must be ≥ 512MB" |
| `PORT_CONFLICT` | 6 | "Port 8080 is already in use by project 'other-project'" |
| `INSUFFICIENT_RESOURCES` | 4 | "Insufficient RAM: need 8192MB, 6000MB available" |
| `INFRA_EXISTS` | 3 | "Infrastructure 'project1' already exists (state: running)" |
| `PROVIDER_NOT_AVAILABLE` | 5 | "Provider 'libvirt' is not installed or not configured" |
| `PROVISIONING_FAILED` | 7 | "Ansible playbook failed: task 'Install Nginx' returned non-zero exit code 1" |
