<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.0
Rationale: Initial constitution ratification - establishing governance for Vagrantp template-driven infrastructure project.

Modified Principles: N/A (initial version)

Added Sections:
- Core Principles (5 principles)
- Infrastructure Standards
- Development Workflow
- Governance

Removed Sections: N/A

Templates Requiring Updates:
✅ .specify/templates/plan-template.md - Constitution Check section already in place
✅ .specify/templates/spec-template.md - Requirements and testing sections aligned
✅ .specify/templates/tasks-template.md - Test-first discipline embedded in template
✅ .opencode/command/speckit.plan.md - Constitution validation workflow defined
✅ .opencode/command/speckit.tasks.md - Task organization aligned with principles

Follow-up TODOs: None
-->

# Vagrantp Constitution

## Core Principles

### I. Template-Driven Architecture

Infrastructure MUST be template-driven with environment variable configuration. The master-template pattern allows instantiating projects without manual Vagrantfile creation. All configuration MUST use .env files or similar parameterization. Templates MUST be self-contained and reusable across projects.

**Rationale**: Enables rapid project setup, ensures consistency, and eliminates boilerplate code duplication across infrastructure projects.

### II. Network Flexibility

Infrastructure MUST support flexible networking including bridge mode. Fixed IP assignment MUST be required. Network configuration MUST be parameterizable. Network topologies MUST support both VM and container workloads seamlessly.

**Rationale**: Provides adaptability for different deployment scenarios while maintaining predictable network addressing for service communication.

### III. Automated Provisioning

All infrastructure MUST be provisioned via Ansible. Provisioning scripts MUST be idempotent. Ansible playbooks MUST be template-driven and follow the same parameterization pattern as the infrastructure templates.

**Rationale**: Ensures consistent, reproducible infrastructure setup across environments and enables configuration management at scale.

### IV. Test-First Operations (NON-NEGOTIABLE)

Every operation (up, ssh, down, rm) MUST be tested. Integration tests mandatory for full lifecycle testing. Infrastructure state MUST be verifiable at each step. Tests MUST cover VM lifecycle, container lifecycle, and network connectivity.

**Rationale**: Prevents infrastructure drift, catches configuration errors early, and ensures reliability of infrastructure operations.

### V. Container Support

Infrastructure MUST support Podman containers. Containers MUST integrate with VM networking. Container deployment MUST follow the same testing discipline as VMs. Container configurations MUST be template-driven.

**Rationale**: Enables modern containerized workloads while maintaining infrastructure consistency and operational reliability.

## Infrastructure Standards

### Technology Stack

- **Virtualization**: Vagrant with provider flexibility (VirtualBox, libvirt, etc.)
- **Containers**: Podman (rootless preferred)
- **Provisioning**: Ansible
- **Configuration**: .env files with variable substitution
- **Testing**: Automated tests for all lifecycle operations (up, ssh, down, rm)

### Networking Requirements

- Bridge mode MUST be supported
- Fixed IP assignment MUST be possible to configure when applicable
- Network isolation MUST be available between projects
- VM-to-container networking MUST be transparent
- DNS resolution MUST be consistent across VMs and containers

### Provisioning Requirements

- Ansible playbooks MUST be idempotent
- Playbooks MUST support dry-run mode
- Provisioning MUST be testable in isolation
- Secrets MUST use environment variables, never hardcoded

### Testing Requirements

- Unit tests for Ansible roles are not required. It is assumed that they work
- Integration tests for VM operations
- Integration tests for container operations
- Network connectivity tests
- State validation tests after each operation

## Development Workflow

### Template Creation

1. Design infrastructure architecture
2. Create template with parameterized values
3. Define .env file structure
4. Write Ansible provisioning playbooks
5. Implement lifecycle tests (up, ssh, down, rm)
6. Document template usage and parameters

### Template Instantiation

1. Configure .env file with project-specific values
2. Validate configuration
3. Deploy infrastructure
4. Verify state and connectivity
5. Allow for an extra provision of a local playbook (user's responsibility)

### Quality Gates

- Network connectivity MUST be verified
- Provisioning MUST be idempotent
- Documentation MUST be complete and accurate

## Governance

### Amendment Procedure

Constitution amendments require:
1. Documented rationale for change
2. Impact analysis on existing templates
3. Migration plan for affected projects
4. Approval via PR with constitutional compliance review

### Versioning Policy

Constitution follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Backward incompatible principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

All PRs MUST verify constitutional compliance:
- Template-driven architecture MUST be maintained
- Network flexibility MUST be preserved
- Ansible provisioning MUST be used
- Infrastructure deploy and provision MUST work for lifecycle operations
- Container support MUST be maintained

Complexity additions MUST be justified in plan.md with alternative analysis.

### Runtime Guidance

Use implementation plans and task checklists for development guidance. Constitutional violations require explicit justification and approval.

**Version**: 1.0.0 | **Ratified**: 2025-12-29 | **Last Amended**: 2025-12-29
