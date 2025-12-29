# CLI API Contract: Vagrantp

**Version**: 1.0.0
**Feature**: Template-Driven Infrastructure (001-template-driven-infra)
**Date**: 2025-12-29

## Overview

This document defines the contract for the `vagrantp` CLI wrapper commands. While this is a CLI tool (not a REST API), we use OpenAPI 3.0 format to provide a structured contract for the command interface, parameters, and responses.

---

## Base Command

```bash
vagrantp <command> [options]
```

---

## Commands

### 1. up - Create and Start Infrastructure

**Description**: Creates and starts infrastructure (VM or container) based on the .env configuration in the current project directory.

**Endpoint**: `POST /up` (conceptual)

**Request Parameters**:

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--dry-run` | boolean | No | Validate configuration without creating infrastructure | `false` |
| `--no-provision` | boolean | No | Skip provisioning step | `false` |

**Request Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `X-Working-Directory` | Yes | Absolute path to project directory (derived from PWD) |

**Response Schema**:

**Success Response (200)**:
```json
{
  "success": true,
  "message": "Infrastructure created and started successfully",
  "infrastructure": {
    "id": "project1",
    "type": "vm",
    "state": "running",
    "resources": {
      "memory_mb": 8192,
      "cpus": 4,
      "disk_gb": 50
    },
    "networking": {
      "mode": "bridge",
      "ip_address": "192.168.1.100",
      "ports": [
        {
          "host": 8080,
          "container": 80,
          "protocol": "tcp"
        }
      ]
    },
    "access": {
      "ssh_command": "ssh av@192.168.1.100",
      "web_urls": [
        "http://192.168.1.100:8080"
      ]
    }
  },
  "provisioning": {
    "executed": true,
    "playbook": "./playbooks/site.yml",
    "duration_seconds": 45
  },
  "next_steps": [
    "Run 'vagrantp ssh' to connect to your infrastructure",
    "Access web services at http://192.168.1.100:8080"
  ]
}
```

**Error Responses**:

**400 Bad Request - Invalid Configuration**:
```json
{
  "error": {
    "code": "CONFIG_INVALID",
    "message": "Invalid configuration in .env file",
    "details": "MEMORY must be at least 512MB, got: 256",
    "field": "MEMORY",
    "line": 5,
    "suggestion": "Set MEMORY=512 or higher in .env file"
  }
}
```

**409 Conflict - Infrastructure Already Exists**:
```json
{
  "error": {
    "code": "INFRA_EXISTS",
    "message": "Infrastructure already exists for this project",
    "details": "Infrastructure 'project1' is currently in 'running' state",
    "suggestion": "Run 'vagrantp ssh' to connect, or 'vagrantp stop' then 'vagrantp rm' to recreate"
  }
}
```

**503 Service Unavailable - Insufficient Resources**:
```json
{
  "error": {
    "code": "INSUFFICIENT_RESOURCES",
    "message": "Insufficient host resources",
    "details": "Need 8192MB RAM, only 6000MB available",
    "suggestion": "Stop other running projects, or reduce MEMORY in .env file"
  }
}
```

**Example CLI Output**:

```bash
$ vagrantp up
✓ Configuration validated
→ Starting infrastructure...
⠹ Creating VM [██████████████████] 100% (2m15s)
⠹ Booting VM... [DONE]
⠹ Running Ansible provisioning [████████████░░░░] 67% (ETA: 15s)
   - Installing dependencies... [DONE]
   - Configuring services... [IN PROGRESS]
✓ Infrastructure is ready
  ID: project1
  Type: VM
  State: running
  IP: 192.168.1.100
  Ports: 8080:80

Next steps:
  → Run 'vagrantp ssh' to connect
  → Access web services at http://192.168.1.100:8080
```

---

### 2. ssh - Connect to Infrastructure

**Description**: Establishes an SSH connection to the running infrastructure.

**Endpoint**: `POST /ssh` (conceptual)

**Request Parameters**:

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--command` | string | No | Execute single command and exit | N/A (interactive shell) |

**Request Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `X-Working-Directory` | Yes | Absolute path to project directory (derived from PWD) |

**Response Schema**:

**Success Response (200)**:
```json
{
  "success": true,
  "message": "SSH connection established",
  "connection": {
    "host": "192.168.1.100",
    "port": 22,
    "user": "av",
    "key": "/home/av/.ssh/id_rsa"
  }
}
```

**Error Responses**:

**404 Not Found - Infrastructure Not Running**:
```json
{
  "error": {
    "code": "INFRA_NOT_RUNNING",
    "message": "Infrastructure is not running",
    "details": "Infrastructure 'project1' is in 'stopped' state",
    "suggestion": "Run 'vagrantp up' to start the infrastructure"
  }
}
```

**503 Service Unavailable - SSH Connection Failed**:
```json
{
  "error": {
    "code": "SSH_CONNECTION_FAILED",
    "message": "Failed to establish SSH connection",
    "details": "Connection timeout after 30 seconds",
    "troubleshooting": [
      "Verify infrastructure is running with 'vagrantp status'",
      "Check network connectivity to 192.168.1.100",
      "Verify SSH service is running in the infrastructure",
      "Check firewall rules on host system"
    ]
  }
}
```

**Example CLI Output**:

```bash
$ vagrantp ssh
⠹ Establishing SSH connection...
⠹ Authenticating...
✓ Connected
[av@project1 ~]$
```

**Single Command Execution**:

```bash
$ vagrantp ssh --command "cat /etc/os-release"
⠹ Establishing SSH connection...
⠹ Executing command...
NAME="Arch Linux"
ID=arch
PRETTY_NAME="Arch Linux"
✓ Command completed
```

---

### 3. stop - Stop Infrastructure

**Description**: Stops the running infrastructure gracefully.

**Endpoint**: `POST /stop` (conceptual)

**Request Parameters**:

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--force` | boolean | No | Force stop without graceful shutdown | `false` |

**Request Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `X-Working-Directory` | Yes | Absolute path to project directory (derived from PWD) |

**Response Schema**:

**Success Response (200)**:
```json
{
  "success": true,
  "message": "Infrastructure stopped successfully",
  "infrastructure": {
    "id": "project1",
    "state": "stopped"
  }
}
```

**Error Responses**:

**404 Not Found - Infrastructure Not Found**:
```json
{
  "error": {
    "code": "INFRA_NOT_FOUND",
    "message": "Infrastructure not found",
    "details": "No infrastructure exists for project 'project1'",
    "suggestion": "Run 'vagrantp up' to create infrastructure"
  }
}
```

**409 Conflict - Infrastructure Already Stopped**:
```json
{
  "error": {
    "code": "INFRA_ALREADY_STOPPED",
    "message": "Infrastructure is already stopped",
    "details": "Infrastructure 'project1' is already in 'stopped' state",
    "suggestion": "No action needed"
  }
}
```

**Example CLI Output**:

```bash
$ vagrantp stop
⠹ Sending shutdown signal...
⠹ Waiting for graceful shutdown [████████░░░░░░] 40%
⠹ Waiting for graceful shutdown [████████████░░░] 80%
⠹ Waiting for graceful shutdown [████████████████] 100% (12s)
✓ Infrastructure stopped
```

**Force Stop**:

```bash
$ vagrantp stop --force
⚠ Force stopping infrastructure
⠹ Sending kill signal...
✓ Infrastructure stopped forcefully (2s)
```

---

### 4. rm - Remove Infrastructure

**Description**: Removes the infrastructure and all associated resources.

**Endpoint**: `DELETE /infra` (conceptual)

**Request Parameters**:

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--force` | boolean | No | Force removal without stopping first | `false` |

**Request Headers**:

| Header | Required | Description |
|--------|----------|-------------|
| `X-Working-Directory` | Yes | Absolute path to project directory (derived from PWD) |

**Response Schema**:

**Success Response (200)**:
```json
{
  "success": true,
  "message": "Infrastructure removed successfully",
  "infrastructure": {
    "id": "project1"
  },
  "cleanup": {
    "disk_images": true,
    "network_config": true,
    "snapshots": true,
    "shared_folders": true
  }
}
```

**Error Responses**:

**404 Not Found - Infrastructure Not Found**:
```json
{
  "error": {
    "code": "INFRA_NOT_FOUND",
    "message": "Infrastructure not found",
    "details": "No infrastructure exists for project 'project1'",
    "suggestion": "No action needed"
  }
}
```

**409 Conflict - Infrastructure Still Running**:
```json
{
  "error": {
    "code": "INFRA_RUNNING",
    "message": "Infrastructure is still running",
    "details": "Infrastructure 'project1' is in 'running' state",
    "suggestion": "Run 'vagrantp stop' first, or use 'vagrantp rm --force'"
  }
}
```

**Example CLI Output**:

```bash
$ vagrantp rm
⚠ Warning: This will permanently remove infrastructure 'project1'
→ Type 'yes' to confirm: yes
⠹ Cleaning up resources...
   - Removing VM data [████████████░░░░░░] 50%
   - Cleaning up network configuration [████████████████] 100%
   - Removing shared folders [DONE]
   - Cleaning up snapshots [DONE]
✓ Infrastructure removed (23s)
```

**Force Remove**:

```bash
$ vagrantp rm --force
⚠ Warning: Force removing running infrastructure
→ Type 'yes' to confirm: yes
⠹ Stopping infrastructure... [DONE]
⠹ Cleaning up resources...
   - Removing VM data [████████████████] 100%
   - Cleaning up network configuration [DONE]
   - Removing shared folders [DONE]
   - Cleaning up snapshots [DONE]
✓ Infrastructure removed (15s)
```

---

## Status Command (Internal)

**Description**: Get current status of infrastructure (internal use, not exposed to users).

**Endpoint**: `GET /status` (conceptual)

**Response Schema**:

```json
{
  "infrastructure": {
    "id": "project1",
    "type": "vm",
    "state": "running",
    "created_at": "2025-12-29T10:30:00Z",
    "updated_at": "2025-12-29T10:30:00Z"
  },
  "resources": {
    "memory_mb": 8192,
    "cpus": 4,
    "disk_gb": 50
  },
  "networking": {
    "mode": "bridge",
    "ip_address": "192.168.1.100",
    "ports": [
      {
        "host": 8080,
        "container": 80,
        "protocol": "tcp"
      }
    ]
  },
  "provisioning": {
    "last_run": "2025-12-29T10:35:00Z",
    "status": "success"
  }
}
```

---

## Configuration File Contract (.env)

**Description**: Configuration file format for project infrastructure.

**File Location**: `.env` in project directory root

**Format**: Key-value pairs (dotenv format)

**Required Fields**:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `INFRA_TYPE` | enum | Infrastructure type (`vm` or `container`) | `vm` |

**Optional Fields**:

| Key | Type | Description | Default | Example |
|-----|------|-------------|---------|---------|
| `INFRA_ID` | string | Custom infrastructure identifier | Project directory name | `myapp-dev` |
| `MEMORY` | string | RAM allocation | `2048` (2GB) | `8192` |
| `CPUS` | integer | CPU cores | `2` | `4` |
| `DISK_SIZE` | string | Disk size | `20G` | `50G` |
| `PROVIDER` | string | VM provider (if VM) | `virtualbox` | `libvirt` |
| `NETWORK_MODE` | enum | Network type | `default` | `bridge` |
| `IP_ADDRESS` | string | Fixed IP address | Auto-assign | `192.168.1.100` |
| `PORTS` | list | Port forwarding rules | `[]` | `8080:80,auto:443` |
| `PROVISIONING_PLAYBOOK` | string | Path to Ansible playbook | N/A | `./playbooks/site.yml` |
| `SSH_USER` | string | SSH username | `root` or system default | `av` |
| `SSH_KEY` | string | Path to SSH private key | Auto-generated or default | `/home/av/.ssh/id_rsa` |

**Validation Rules**:

1. `INFRA_TYPE` must be present and valid (`vm` or `container`)
2. If `INFRA_TYPE=vm`, `PROVIDER` must be present and installed
3. `MEMORY` must be ≥ 512MB (format: `<bytes>` or `<unit>` e.g., `2G`)
4. `CPUS` must be ≥ 1
5. `DISK_SIZE` must be ≥ 5GB
6. `IP_ADDRESS` must be valid IPv4 if specified
7. `PORTS` format: `host:container` or `auto:container`, comma-separated
8. `PROVISIONING_PLAYBOOK` must exist if specified
9. `SSH_KEY` must exist if specified

**Example Configuration**:

```env
# Infrastructure type (required)
INFRA_TYPE=vm

# Resources (optional)
INFRA_ID=myapp-dev
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

---

## Exit Codes

| Code | Meaning | When Returned |
|------|---------|---------------|
| 0 | Success | Command completed successfully |
| 1 | General Error | Unexpected error occurred |
| 2 | Configuration Error | Invalid or missing configuration |
| 3 | Infrastructure Exists | Infrastructure already exists (for `up`) |
| 4 | Insufficient Resources | Host lacks required resources |
| 5 | Provider Not Available | Provider not installed or not configured |
| 6 | Port Conflict | Port already in use |
| 7 | Provisioning Failed | Ansible playbook execution failed |

---

## Error Response Format (JSON)

When errors occur, the system outputs structured error information:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string",
    "field": "string",        // Optional: for configuration errors
    "line": integer,          // Optional: for configuration errors
    "suggestion": "string",   // Optional: actionable guidance
    "troubleshooting": [      // Optional: troubleshooting steps
      "string",
      "string"
    ]
  }
}
```

---

## Performance Requirements

| Metric | Requirement |
|--------|-------------|
| Startup to first output | < 100ms |
| Configuration validation | < 200ms |
| Wrapper overhead (fast ops) | < 100ms |
| Wrapper overhead (slow ops) | < 500ms |
| Status checks | < 500ms |
| .env file loading | < 30ms |
| Process spawning | < 50ms |

---

## Security Considerations

1. **SSH Keys**: Never log or display SSH key contents
2. **Passwords**: Use environment variables or prompt interactively, never store in .env
3. **Privilege Escalation**: Require sudo only for provider operations, not wrapper
4. **Input Validation**: Validate all .env values before use
5. **Command Injection**: Use subprocess with proper argument escaping
6. **File Permissions**: Ensure .env file has appropriate permissions (600)
7. **Network Isolation**: Use bridge mode for project isolation when configured
