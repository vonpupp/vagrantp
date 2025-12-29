# Tasks: Template-Driven Infrastructure

**Input**: Design documents from `/specs/001-template-driven-infra/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This feature does not explicitly request TDD approach. Tests will be implemented in integration layer only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths below assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure: src/cli/, src/config/, src/vagrant/, src/podman/, src/provision/, src/utils/, tests/integration/, tests/unit/, tests/fixtures/, templates/, ansible/
- [X] T002 Create pyproject.toml with dependencies: invoke>=2.0, python-dotenv>=1.0.0, vagrant>=2.3, pytest>=7.0, pytest-mock>=3.10
- [X] T003 Create requirements.txt from pyproject.toml dependencies
- [X] T004 Create setup.py for package installation
- [X] T005 [P] Create __init__.py files in all src/ directories
- [X] T006 [P] Create README.md with project overview and installation instructions
- [X] T007 [P] Create .gitignore for Python, Vagrant, and Podman artifacts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create configuration file parser in src/config/parser.py that loads and parses .env files from current directory
- [X] T009 [P] Create configuration validator in src/config/parser.py that validates INFRA_TYPE, MEMORY, CPUS, DISK_SIZE per data-model.md rules
- [X] T010 [P] Create infrastructure state manager in src/utils/helpers.py for tracking infrastructure states (not_created, creating, running, stopped, removing)
- [X] T011 Create base CLI task structure in src/cli/main.py using Invoke framework with command registration
- [X] T012 [P] Create error handling module in src/utils/helpers.py with structured error classes matching contracts/cli-api.md error codes
- [X] T013 [P] Create utility functions in src/utils/helpers.py for file operations, shell command execution, and logging
- [X] T014 Create template base class in src/utils/helpers.py for ERB template rendering
- [X] T015 Create default Ansible playbook structure in ansible/site.yml and ansible/roles/base/
- [X] T017 Create test fixture for sample .env configuration in tests/fixtures/sample.env

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create and Manage VM Infrastructure (Priority: P1) 🎯 MVP

**Goal**: Create, SSH into, stop, and remove VM infrastructure from .env configuration

**Independent Test**: Create VM from .env config, verify it runs, SSH into it, stop it, and remove it - delivering complete VM lifecycle management

### Implementation for User Story 1

- [X] T018 [P] [US1] Create VM provider interface in src/vagrant/vm_manager.py with methods: create(), connect(), stop(), remove()
- [X] T019 [P] [US1] Create Vagrantfile template for VMs in templates/vm.erb with configurable resources, networking, and SSH settings
- [X] T020 [P] [US1] Create SSH connection handler in src/vagrant/vm_manager.py that establishes interactive SSH sessions
- [X] T021 [US1] Implement VM creation logic in src/vagrant/vm_manager.py create() that generates Vagrantfile from template and delegates to Vagrant CLI
- [X] T022 [US1] Implement VM stop logic in src/vagrant/vm_manager.py stop() with graceful and force modes
- [X] T023 [US1] Implement VM removal logic in src/vagrant/vm_manager.py remove() that cleans up all VM resources including disk images and network config
- [X] T023a [US1] Verify network connectivity in src/vagrant/vm_manager.py after VM creation to ensure IP is reachable and SSH port is accessible (ping and port check)
- [X] T024 [US1] Implement up CLI command in src/cli/main.py that reads .env, validates config, creates VM using vm_manager, and displays simple status messages
- [X] T025 [US1] Implement ssh CLI command in src/cli/main.py that reads .env, establishes SSH connection using vm_manager
- [X] T026 [US1] Implement stop CLI command in src/cli/main.py that reads .env, stops VM using vm_manager with --force option
- [X] T027 [US1] Implement rm CLI command in src/cli/main.py that reads .env, removes VM using vm_manager with --force option and confirmation prompt
- [X] T028 [US1] Add idempotency check in up CLI command to prevent duplicate VM creation (FR-015)
- [X] T029 [US1] Add error messages in all CLI commands per contracts/cli-api.md (CONFIG_MISSING, CONFIG_INVALID, INFRA_EXISTS, PROVIDER_NOT_AVAILABLE)
- [X] T030 [US1] Create integration test in tests/integration/test_vm_lifecycle.py for full VM lifecycle (up → ssh → stop → rm)
- [X] T033 [US1] Create unit tests in tests/unit/test_vm_manager.py for VM manager methods using mocked Vagrant CLI calls
- [X] T034 [US1] Create unit tests in tests/unit/test_config_parser.py for .env parsing and validation with VM-specific test cases

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Create and Manage Container Infrastructure (Priority: P2)

**Goal**: Create, SSH into, stop, and remove Podman containers from .env configuration

**Independent Test**: Create container from .env config, verify it runs, SSH into it, stop it, and remove it - delivering container management without VM dependencies

### Implementation for User Story 2

- [X] T035 [P] [US2] Create container provider interface in src/podman/container_manager.py with methods: create(), connect(), stop(), remove()
- [X] T036 [P] [US2] Create Podman spec template in templates/container.erb for container generation
- [X] T037 [P] [US2] Create SSH connection handler in src/podman/container_manager.py for container SSH access
- [X] T038 [US2] Implement container creation logic in src/podman/container_manager.py create() using Podman CLI with resource limits and networking
- [X] T039 [US2] Implement container stop logic in src/podman/container_manager.py stop() with graceful and force modes
- [X] T040 [US2] Implement container removal logic in src/podman/container_manager.py remove() that cleans up container and associated volumes/networks
- [X] T041 [US2] Extend up CLI command in src/cli/main.py to detect INFRA_TYPE=container and delegate to container_manager
- [X] T042 [US2] Extend ssh CLI command in src/cli/main.py to support container SSH via container_manager
- [X] T043 [US2] Extend stop CLI command in src/cli/main.py to support container stop
- [X] T044 [US2] Extend rm CLI command in src/cli/main.py to support container removal
- [X] T045 [US2] Add container-specific validation in src/config/parser.py for container-only fields (MEMORY, CPUS without DISK_SIZE)
- [X] T046 [US2] Add idempotency check for containers in up CLI command
- [X] T047 [US2] Create integration test in tests/integration/test_container_lifecycle.py for full container lifecycle (up → ssh → stop → rm)
- [X] T048 [US2] Create unit tests in tests/unit/test_container_manager.py for container manager methods using mocked Podman CLI calls
- [X] T049 [US2] Create unit tests in tests/unit/test_config_parser.py for container-specific validation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Configure Infrastructure Resources (Priority: P3)

**Goal**: Customize infrastructure resources (RAM, CPU, disk, networking, port forwarding) via .env configuration

**Independent Test**: Create VMs/containers with different resource configurations and verify they match the .env specification

### Implementation for User Story 3

- [X] T050 [P] [US3] Extend configuration parser in src/config/parser.py to parse MEMORY with unit parsing (G, M) and validate minimum 512MB
- [X] T051 [P] [US3] Extend configuration parser in src/config/parser.py to parse CPUS and validate minimum 1
- [X] T052 [P] [US3] Extend configuration parser in src/config/parser.py to parse DISK_SIZE with unit parsing (G, M) and validate minimum 5GB
- [X] T053 [P] [US3] Extend configuration parser in src/config/parser.py to parse NETWORK_MODE (bridge|default) and set defaults
- [X] T054 [P] [US3] Extend configuration parser in src/config/parser.py to parse IP_ADDRESS and validate IPv4 format if specified
- [X] T055 [P] [US3] Extend configuration parser in src/config/parser.py to parse PORTS as list of host:container mappings
- [X] T056 [US3] Extend VM manager in src/vagrant/vm_manager.py to apply MEMORY, CPUS, DISK_SIZE to Vagrantfile template
- [X] T057 [US3] Extend VM manager in src/vagrant/vm_manager.py to configure NETWORK_MODE (bridge|default) in Vagrantfile template
- [X] T058 [US3] Extend VM manager in src/vagrant/vm_manager.py to configure port forwarding from PORTS in Vagrantfile template
- [X] T059 [US3] Extend VM manager in src/vagrant/vm_manager.py to configure fixed IP from IP_ADDRESS in Vagrantfile template
- [X] T060 [US3] Extend container manager in src/podman/container_manager.py to apply MEMORY, CPUS to podman run CLI flags
- [X] T061 [US3] Extend container manager in src/podman/container_manager.py to configure NETWORK_MODE in podman network settings
- [X] T062 [US3] Extend container manager in src/podman/container_manager.py to configure port forwarding from PORTS in podman publish flags
- [X] T063 [US3] Add port conflict detection in src/config/parser.py to check if host ports are already in use
- [X] T064 [US3] Add network interface validation in src/vagrant/vm_manager.py to verify bridge exists for NETWORK_MODE=bridge
- [X] T065 [US3] Add error messages for resource configuration errors (invalid MEMORY format, port conflicts, missing bridge interface)
- [X] T066 [US3] Create unit tests in tests/unit/test_config_parser.py for resource parsing (MEMORY units, CPUS, DISK_SIZE units)
- [X] T067 [US3] Create unit tests in tests/unit/test_config_parser.py for networking configuration (NETWORK_MODE, IP_ADDRESS, PORTS)
- [X] T068 [US3] Create unit tests in tests/unit/test_vm_manager.py for resource application to Vagrantfile template
- [X] T069 [US3] Create unit tests in tests/unit/test_container_manager.py for resource application to Podman CLI flags

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - Provision Infrastructure Automatically (Priority: P3)

**Goal**: Run Ansible provisioning scripts automatically after infrastructure creation

**Independent Test**: Create infrastructure and verify that automated provisioning runs and applies the specified configuration

### Implementation for User Story 4

- [ ] T070 [P] [US4] Create provisioning orchestrator in src/provision/ansible.py with execute() method that runs Ansible playbooks
- [ ] T071 [P] [US4] Extend configuration parser in src/config/parser.py to parse PROVISIONING_PLAYBOOK path and validate file exists
- [ ] T072 [P] [US4] Extend configuration parser in src/config/parser.py to parse optional PROVISIONING_VARS path for Ansible variables
- [ ] T073 [US4] Implement Ansible playbook execution in src/provision/ansible.py execute() with output capture and exit code handling
- [ ] T074 [US4] Implement SSH connection verification in src/provision/ansible.py before running Ansible playbook
- [ ] T075 [US4] Add dry-run mode support in src/provision/ansible.py execute() for Ansible playbook validation
- [ ] T076 [US4] Integrate provisioning into up CLI command in src/cli/main.py with --no-provision option to skip provisioning
- [ ] T077 [US4] Add provisioning progress indicators in up CLI command showing playbook execution progress
- [ ] T078 [US4] Add error handling for provisioning failures with clear error messages showing failure point (exit code 7)
- [ ] T079 [US4] Add idempotency support for provisioning by checking if provisioning already succeeded
- [ ] T080 [US4] Create default Ansible playbook in ansible/site.yml that installs base packages (git, vim, tmux)
- [ ] T081 [US4] Create integration test in tests/integration/test_vm_lifecycle.py for VM provisioning workflow
- [ ] T082 [US4] Create integration test in tests/integration/test_container_lifecycle.py for container provisioning workflow
- [ ] T083 [US4] Create unit tests in tests/unit/test_ansible.py for provisioning orchestrator with mocked Ansible CLI calls

**Checkpoint**: User Story 4 adds automated provisioning capability

---

## Phase 7: User Story 5 - Validate Configuration Before Deployment (Priority: P3)

**Goal**: Validate .env configuration files before creating infrastructure to avoid wasted time on failed deployments

**Independent Test**: Run validation on various .env files and receive accurate feedback about validity issues

### Implementation for User Story 5

- [ ] T084 [P] [US5] Extend configuration parser in src/config/parser.py to add validate() method that returns ValidationResult with errors and warnings
- [ ] T085 [P] [US5] Add validation for missing required fields (INFRA_TYPE, PROVIDER for VM) with clear error messages
- [ ] T086 [P] [US5] Add validation for invalid field values (negative MEMORY, CPUS < 1, invalid INFRA_TYPE)
- [ ] T087 [P] [US5] Add validation for port conflicts across existing infrastructure instances
- [ ] T088 [P] [US5] Add validation for resource availability (check host memory and CPU availability)
- [ ] T089 [US5] Implement validate CLI command in src/cli/main.py that runs validation and displays errors without creating infrastructure
- [ ] T090 [US5] Add --dry-run option to up CLI command in src/cli/main.py that runs validation only
- [ ] T091 [US5] Add validation error output format with field names, line numbers (if available), and suggestions
- [ ] T092 [US5] Create unit tests in tests/unit/test_config_parser.py for validation error cases (missing fields, invalid values, port conflicts)
- [ ] T093 [US5] Create test fixtures in tests/fixtures/ for invalid .env configurations (missing_fields.env, invalid_values.env, port_conflict.env)

**Checkpoint**: User Story 5 adds pre-deployment validation capability

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T094 [P] Update README.md with quick start guide and configuration reference
- [X] T095 [P] Add command-line help text in src/cli/main.py for all commands (--help)
- [X] T096 [P] Add version command in src/cli/main.py (--version)
- [ ] T097 Add signal handling for Ctrl+C in all CLI commands to gracefully cancel operations with cleanup
- [ ] T098 Add logging infrastructure in src/utils/helpers.py with configurable log levels and output to file
- [ ] T101 [P] Add network connectivity verification test in tests/integration/ that verifies IP reachability and port accessibility for both VMs and containers per Constitution L115
- [ ] T102 [P] Add unit tests for error handling in tests/unit/test_error_handling.py covering all error codes from contracts/cli-api.md
- [ ] T103 [P] Add integration tests for edge cases in tests/integration/ (infrastructure already exists, insufficient resources, missing .env, provider not available)
- [ ] T103 Security hardening: Add file permission checks in src/config/parser.py to ensure .env has appropriate permissions (600)
- [ ] T104 Security hardening: Add input validation in src/utils/helpers.py to prevent command injection in subprocess calls
- [ ] T105 Run quickstart.md validation: Test all examples from quickstart.md end-to-end
- [ ] T106 Create comprehensive documentation for .env configuration in docs/CONFIGURATION.md
- [ ] T107 Create troubleshooting guide in docs/TROUBLESHOOTING.md with common error scenarios
- [ ] T108 Add code cleanup: Remove unused imports, fix linting issues, ensure type hints on all functions
- [ ] T109 Add integration with AGENTS.md: Update AGENTS.md with finalized tech stack if needed
- [ ] T110 Final validation: Run all tests (unit + integration) and ensure 100% pass rate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1, shares CLI commands
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1 and US2 with resource configuration
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Adds provisioning to both VM and container workflows
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Adds validation that benefits all stories

### Within Each User Story

- Provider interfaces before CLI command implementations
- Configuration parsing before validation
- Core implementation before tests
- Tests after implementation (TDD not requested)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T005, T006, T007)
- All Foundational tasks marked [P] can run in parallel (T009, T010, T012, T013, T014, T017)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Within US1: VM provider interface and SSH handler can run in parallel (T018, T020)
- Within US2: Container provider interface, template, and SSH handler can run in parallel (T035, T036, T037)
- Within US3: All configuration parsing extensions can run in parallel (T050-T055)
- Within US4: Provisioning orchestrator and config parsing can run in parallel (T070, T071, T072)
- Within US5: All validation extensions can run in parallel (T085-T088)
- Polish tasks marked [P] can run in parallel (T094, T095, T101, T103)

---

## Parallel Example: User Story 1

```bash
# Launch provider interface and SSH handler together:
Task: "Create VM provider interface in src/vagrant/vm_manager.py"
Task: "Create SSH connection handler in src/vagrant/vm_manager.py"

# Launch implementation tasks together:
Task: "Implement VM creation logic in src/vagrant/vm_manager.py create()"
Task: "Implement VM stop logic in src/vagrant/vm_manager.py stop()"
Task: "Implement VM removal logic in src/vagrant/vm_manager.py remove()"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T017) - CRITICAL
3. Complete Phase 3: User Story 1 (T018-T034)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Create .env file with INFRA_TYPE=vm
   - Run `vagrantp up` to create VM
   - Run `vagrantp ssh` to connect
   - Run `vagrantp stop` to stop VM
   - Run `vagrantp rm` to remove VM
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Polish (Phase 8) → Final release
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (VM infrastructure)
   - Developer B: User Story 2 (Container infrastructure)
   - Developer C: User Story 3 (Resource configuration)
3. After P1-P3 complete:
   - Developer A: User Story 4 (Provisioning)
   - Developer B: User Story 5 (Validation)
4. Team converges on Polish phase
5. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are implemented in integration layer (not TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MVP = User Story 1 only (VM lifecycle management)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tasks follow the strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
