# Research Findings: Template-Driven Infrastructure

**Feature**: Template-Driven Infrastructure (001-template-driven-infra)
**Date**: 2025-12-29
**Phase**: Phase 0 - Research and Technology Decisions

## Summary

This document consolidates research findings for all technical decisions required to implement the template-driven infrastructure system. All items marked as "NEEDS CLARIFICATION" in the Technical Context have been resolved with documented decisions and rationale.

---

## Decision 1: Programming Language and Framework

### **Chosen: Python 3.11+ with Invoke**

**Rationale**:

- **Better Error Handling**: Python's try/except blocks provide structured, catchable exception handling vs Bash's limited exit code checking
- **Superior Testing**: pytest + MockContext provides robust testing infrastructure vs BATS for bash
- **Idempotency Support**: Easier to implement idempotent operations with Python's state management vs Bash's procedural nature
- **Rich Ecosystem**: Built-in libraries for .env parsing (`python-dotenv`), subprocess management, and Ansible orchestration
- **Maintainability**: Type hints, docstrings, and modular code organization vs Bash's procedural complexity
- **Cross-platform**: Excellent compatibility across Linux distributions (bash vs sh vs zsh compatibility issues)

**Alternatives Considered**:

- **Bash with Make**: Rejected due to poor error handling for complex orchestration, difficult testing (BATS vs pytest), limited .env validation, and cross-platform compatibility issues
- **Pure Python (Click/Typer)**: Considered but Invoke is specifically designed for task execution with better subprocess integration and DevOps automation patterns

**Community Preference**:

- Most successful DevOps tools use Python (Ansible: 67.5k stars, Fabric: 15.3k stars, Invoke: 4.7k stars)
- Existing tools in this space are Python-based (pods-compose, py-vm)

---

## Decision 2: Primary Dependencies

### **Chosen Stack**

- **Wrapper Framework**: Invoke (for task execution and CLI interface)
- **Virtualization**: Vagrant with provider flexibility (VirtualBox, libvirt, etc.)
- **Container Runtime**: Podman (rootless preferred)
- **Provisioning**: Ansible
- **Configuration Parsing**: python-dotenv
- **Testing**: pytest with MockContext

**Rationale**:

- Invoke provides task execution framework specifically designed for DevOps automation
- Vagrant is the industry standard for VM management with multiple provider support
- Podman provides daemonless container architecture with rootless operation security
- Ansible is the industry standard for configuration management (as required by constitution)
- python-dotenv provides robust .env file parsing with validation support
- pytest is the industry standard Python testing framework with extensive plugin ecosystem

**Alternatives Considered**:

- **Makefile**: Rejected due to Bash scripting complexity, poor error handling, and difficult testing
- **Chef/Puppet**: Rejected in favor of Ansible (constitution requirement)

---

## Decision 3: Testing Framework

### **Chosen: pytest with comprehensive test strategy**

**Test Pyramid**:

```
        E2E Tests (5-10%)
      ────────────────
     Integration Tests (20-30%)
   ────────────────────────
  Unit Tests (60-70%)
───────────────────────
```

**Testing Strategy**:

**Unit Tests (60-70%)**:

- Config parsing/validation logic
- .env file loading and parsing
- Command argument parsing
- State machine logic
- Network configuration generation
- Mock Vagrant/Podman/Ansible commands
- Test data transformation and formatting

**Integration Tests (20-30%)**:

- Full lifecycle: up → ssh → stop → rm
- State validation after each operation
- Idempotency verification (running `up` twice)
- Error handling and validation
- Configuration file edge cases
- Mocked infrastructure with simulated responses

**E2E Tests (5-10%)**:

- Real VM/container creation with lightweight images
- Full provisioning workflow
- Network connectivity verification
- Run in CI with proper cleanup
- Use test fixtures to ensure teardown

**External Dependency Handling**:

- **Mocking**: Use pytest monkeypatch to stub Vagrant, Podman, and Ansible subprocess calls in unit/integration tests
- **Mock Responses**: Create mock response objects for Vagrant/Podman JSON output
- **Real Infrastructure**: Use lightweight VM images (Alpine, minimal Ubuntu) and Podman small base images (alpine, scratch) for E2E tests

**Alternatives Considered**:

- **BATS (Bash Automated Testing System)**: Rejected due to limited features, no built-in mocking, and smaller plugin ecosystem compared to pytest

---

## Decision 4: Performance Goals

### **Performance Targets**

| Metric | Target | Priority |
|--------|--------|----------|
| **Startup to first output** | < 100ms | **CRITICAL** |
| **Wrapper overhead (fast ops < 1s)** | < 100ms | **HIGH** |
| **Wrapper overhead (medium ops 1-10s)** | < 200ms | **HIGH** |
| **Wrapper overhead (slow ops > 10s)** | < 500ms | **MEDIUM** |
| **Status checks** | < 500ms | **HIGH** |
| **Configuration validation** | < 200ms | **MEDIUM** |
| **.env file loading** | < 30ms | **LOW** |
| **Process spawning** | < 50ms | **MEDIUM** |

**Rationale**:

- Based on industry standards from Docker CLI, kubectl, Vagrant CLI
- Nielsen's instant feedback threshold (< 100ms) for perceived responsiveness
- Wrapper overhead should be ≤ 5% of total execution time for operations > 2s
- Infrastructure operations dominated by Vagrant/Podman (not wrapper)

**Validation Criteria**:

- 95th percentile of startup time < 100ms
- 99th percentile of wrapper overhead < 150ms
- Mean wrapper overhead < 80ms

**User Feedback Strategy**:

- **< 1s operations**: Spinner or brief status message
- **1-10s operations**: Spinner + step description
- **10-60s operations**: Progress bar with percentage
- **> 60s operations**: Progress bar + ETA + step details

**Optimization Strategies**:

- Lazy initialization (only load .env when needed)
- Caching (parsed configuration, infrastructure state, SSH connection info)
- Parallel operations (run validation checks in parallel)
- Efficient subprocess handling (direct calls, real-time streaming, signal propagation)
- Optimize file I/O (native file reading, minimize stat() calls)

---

## Decision 5: Constraints

### **Operational Constraints**

1. **Idempotent Operations**:
   - Running `up` multiple times must not create duplicate infrastructure
   - Check infrastructure state before creation
   - Use state tracking with conditionals

2. **CLI Simplicity**:
   - Single command interface: `vagrantp <command>`
   - Commands: `up`, `ssh`, `stop`, `rm`
   - Automatic .env file detection in current directory
   - Clear error messages with actionable guidance

3. **Fast and Responsive**:
   - Print initial output in < 100ms
   - Show progress for operations > 10 seconds
   - Handle long-running operations with progress indicators
   - Allow cancellation (Ctrl-C) with graceful cleanup

4. **Multiple Concurrent Projects**:
   - Project isolation (no shared state between projects)
   - Lock files only for specific project
   - Per-project .env files in each directory
   - No global configuration affecting all projects

**Implementation Strategies**:

- Use Python's type hints for maintainability
- Implement structured exceptions with context
- Use Invoke's task framework for CLI interface
- Modular code organization (cli, config, vagrant, podman, provision, utils)
- Docstrings for all functions and modules

---

## Decision 6: Scale and Scope

### **Concurrent Projects Support**

- **Small to Medium Scale**: 5-15 concurrent projects (typical developer workflow)
- **Large Scale**: 20-50 concurrent projects with careful resource planning
- **Enterprise Scale**: 100+ projects requires cluster management approach

### **Resource Limits Per Project**

**Minimum Requirements**:

- RAM: 512MB - 1GB (container-only projects)
- RAM: 2GB - 4GB (VM-based projects)
- CPU: 0.5 - 2 vCPU cores
- Disk: 5GB - 50GB

**Maximum Reasonable Size**:

- RAM: 16GB per project
- CPU: 8 vCPU cores per project
- Disk: 500GB per project

### **Host-Level Resource Limits**

**For 16GB RAM host**:

- Total VM overhead: ~2-4GB (hypervisor + base OS)
- Available for projects: ~12GB
- Recommended: 3-6 small projects or 2-3 medium projects

**For 32GB RAM host**:

- Total VM overhead: ~4-6GB
- Available for projects: ~26GB
- Recommended: 6-12 small projects or 4-6 medium projects

### **Conflict Resolution Strategies**

**1. Naming Conflicts**:

- Use hierarchical project identification: `<username>/<directory-name>/<project-name>`
- Alternative: UUID-based internal names with collision detection
- Auto-append suffix if collision detected

**2. Port Conflicts**:

- Dynamic port allocation from managed pool (e.g., 8100-8900)
- Auto-assign on project startup
- Fixed ports available via explicit configuration
- Port mapping in project manifest

**3. Resource Contention**:

- Priority system: active (100), background (50), stopped (0)
- Quota enforcement: soft limit (throttle) and hard limit (deny)
- Burst allowance for temporary spikes

### **Resource Management Approach**

- Track per-project metrics (CPU, memory, disk I/O, network I/O, health status)
- Pre-flight checks: verify sufficient host resources, naming conflicts, port availability
- Cgroups v2 integration for enforcement (CPU, memory, I/O, PIDs limits)
- OOM handling: graceful shutdown, swap optimization, priority-based termination

### **Scalability Considerations**

**For 100+ Projects**:

- Horizontal scaling across multiple hosts
- Central orchestration plane (lightweight Kubernetes or similar)
- Container-only projects (lighter than VMs)
- Shared base images (differential storage)
- Lazy loading for inactive projects
- Automated hibernation (swap + suspend VMs)

**Storage Architecture**:

- Tiered storage: /images (shared), /projects (project-specific), /snapshots, /logs
- Deduplication: layer-based storage for containers, Qcow2 copy-on-write for VMs
- Snapshot chains with garbage collection

**Network Architecture**:

- Per-project bridge networks (container mode)
- Isolated VLANs for VMs (hardware virtualization)
- DNS resolution: `<project>.local`
- Service discovery integration

---

## Summary of Resolved Clarifications

| Clarification | Decision | Confidence |
|---------------|----------|------------|
| **Language/Version** | Python 3.11+ with Invoke | High |
| **Primary Dependencies** | Invoke, Vagrant, Podman, Ansible, python-dotenv, pytest | High |
| **Testing** | pytest with 60-70% unit, 20-30% integration, 5-10% E2E | High |
| **Performance Goals** | < 100ms startup, < 5% wrapper overhead, detailed targets defined | High |
| **Constraints** | Idempotent ops, simple CLI, fast & responsive, multi-project support | High |
| **Scale/Scope** | 5-15 concurrent projects, resource limits per project, conflict resolution strategies | Medium |

**All Phase 0 research complete. All NEEDS CLARIFICATION items resolved.**
