# Implementation Plan: Template-Driven Infrastructure

**Branch**: `001-template-driven-infra` | **Date**: 2025-12-29 | **Spec**: /specs/001-template-driven-infra/spec.md
**Input**: Feature specification from `/specs/001-template-driven-infra/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a template-driven infrastructure system using Vagrant that allows developers to create VMs and Podman containers from .env configuration files without writing individual Vagrantfiles. The system will provide wrapper commands (up, ssh, stop, rm) that automatically read configuration from the current project directory and use the project directory name as the infrastructure identifier. All infrastructure will be provisioned via Ansible playbooks.

## Technical Context

**Language/Version**: Python 3.x (for invoke-based wrapper) or Bash (for make-based wrapper)
**Primary Dependencies**: Vagrant, VirtualBox/libvirt, Podman, Ansible, fabric/invoke (preferred) or make
**Storage**: N/A
**Testing**: pytest (for Python wrapper) or Bash testing framework (for Bash wrapper)
**Target Platform**: Linux (host system)
**Project Type**: single
**Constraints**: Idempotent operations, CLI interface must be simple, must support multiple concurrent projects
**Scale/Scope**: No enforced limits - rely on host OS cgroups and kernel resource management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Template-Driven Architecture | ✅ PASS | Spec requires .env configuration files, master-template pattern eliminates boilerplate Vagrantfiles |
| II. Network Flexibility | ✅ PASS | Spec supports bridge and default networking modes, port forwarding configuration, and fixed IP assignment |
| III. Automated Provisioning | ✅ PASS | Spec requires Ansible provisioning with support for user-specified playbooks |
| IV. Test-First Operations | ✅ PASS | Spec includes user stories with testing scenarios, edge cases cover lifecycle operations |
| V. Container Support | ✅ PASS | Spec explicitly requires Podman container support with same CLI interface as VMs |

### Infrastructure Standards Compliance

| Standard | Status | Notes |
|----------|--------|-------|
| Technology Stack: Vagrant, Podman, Ansible | ✅ PASS | All specified in requirements |
| Networking: Bridge mode, fixed IP | ✅ PASS | FR-014, FR-017 support bridge/default networking and fixed IPs |
| Provisioning: Idempotent Ansible | ✅ PASS | FR-007 requires automated provisioning, constitution requires idempotency |
| Testing: Lifecycle operations | ✅ PASS | User Stories 1-2 test VM/container lifecycle (up, ssh, stop, rm) |

### Quality Gates

- [x] Documentation MUST be complete and accurate (Completed in Phase 1)
- [ ] Network connectivity MUST be verified (to be tested in Phase 2)
- [ ] Provisioning MUST be idempotent (to be tested in Phase 2)

**GATE STATUS**: ✅ PASS - Proceed to Phase 0 research

## Post-Design Constitution Re-evaluation

After completing Phase 1 design (research.md, data-model.md, contracts/cli-api.md, quickstart.md), re-evaluating constitutional compliance:

### Core Principles Compliance (Post-Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Template-Driven Architecture | ✅ PASS | .env file schema defined in data-model.md, ERB templates planned for Vagrantfile generation |
| II. Network Flexibility | ✅ PASS | data-model.md defines Networking object with bridge/default modes, IP_ADDRESS, PORTS support |
| III. Automated Provisioning | ✅ PASS | Provisioning object defined, Ansible integration planned, idempotency requirement specified |
| IV. Test-First Operations | ✅ PASS | test strategy defined in research.md (60-70% unit, 20-30% integration, 5-10% E2E) |
| V. Container Support | ✅ PASS | INFRA_TYPE enum supports both 'vm' and 'container', Podman integration planned |

### Infrastructure Standards Compliance (Post-Design)

| Standard | Status | Notes |
|----------|--------|-------|
| Technology Stack | ✅ PASS | Python 3.11+ with Invoke chosen, Vagrant/Podman/Ansible dependencies defined |
| Networking: Bridge mode, fixed IP | ✅ PASS | NETWORK_MODE enum (bridge|default), IP_ADDRESS field, PORTS mapping defined |
| Provisioning: Idempotent Ansible | ✅ PASS | Provisioning object requires type='ansible', dry_run mode supported |
| Testing: Lifecycle operations | ✅ PASS | Test pyramid defined, integration tests for up/ssh/stop/rm planned |

### Quality Gates (Post-Design)

- [x] Documentation MUST be complete and accurate ✅ COMPLETE (research.md, data-model.md, contracts/cli-api.md, quickstart.md all generated)
- [ ] Network connectivity MUST be verified (pending Phase 2 implementation and testing)
- [ ] Provisioning MUST be idempotent (pending Phase 2 implementation and testing)

**POST-DESIGN GATE STATUS**: ✅ PASS - All constitutional requirements addressed in design. Ready for Phase 2 (tasks.md generation via /speckit.tasks command).

## Phase 0 & 1 Artifacts Generated

✓ **research.md** - Technology decisions, dependencies, performance targets, scale/scope analysis
✓ **data-model.md** - Entity definitions, relationships, state machines, validation rules, data flows
✓ **contracts/cli-api.md** - CLI command contracts, request/response schemas, error handling, exit codes
✓ **quickstart.md** - Installation guide, examples, common workflows, troubleshooting
✓ **AGENTS.md** - Updated with Python 3.x, Invoke, Vagrant, Podman, Ansible technologies

## Next Steps

Execute `/speckit.tasks` to generate task breakdown for Phase 2 implementation.

## Project Structure

### Documentation (this feature)

```text
specs/001-template-driven-infra/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
vagrant/
├── src/
│   ├── __init__.py
│   ├── cli/            # CLI interface (invoke tasks or main entry point)
│   │   ├── __init__.py
│   │   └── main.py
│   ├── config/         # .env parsing and validation
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── vagrant/        # Vagrant operations (VM creation, management)
│   │   ├── __init__.py
│   │   └── vm_manager.py
│   ├── podman/         # Podman operations (container creation, management)
│   │   ├── __init__.py
│   │   └── container_manager.py
│   ├── provision/      # Ansible provisioning orchestration
│   │   ├── __init__.py
│   │   └── ansible.py
│   └── utils/          # Utilities (file operations, shell commands)
│       ├── __init__.py
│       └── helpers.py
├── templates/          # Vagrantfile templates
│   ├── vm.erb
│   └── container.erb
├── ansible/            # Default Ansible playbooks
│   ├── site.yml
│   └── roles/
│       └── base/
├── tests/
│   ├── __init__.py
│   ├── integration/    # Full lifecycle tests (up, ssh, stop, rm)
│   │   ├── test_vm_lifecycle.py
│   │   └── test_container_lifecycle.py
│   ├── unit/           # Unit tests for individual components
│   │   ├── test_config_parser.py
│   │   ├── test_vm_manager.py
│   │   └── test_container_manager.py
│   └── fixtures/       # Test data and sample configs
│       └── sample.env
├── pyproject.toml      # Python dependencies and project config
├── requirements.txt
├── README.md
└── setup.py
```

**Structure Decision**: Single project structure chosen as this is a CLI tool/wrapper that provides a unified interface for managing both VM and container infrastructure. The codebase is organized by functional area (cli, config, vagrant, podman, provision, utils) with templates for Vagrantfile generation and default Ansible playbooks for provisioning.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
