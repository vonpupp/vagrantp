# Feature Specification: Template-Driven Infrastructure

**Feature Branch**: `001-template-driven-infra`
**Created**: 2025-12-29
**Status**: Draft
**Input**: User description: "I use a home server to code with AI. For security and privacy, I have the AI running inside a VM within that host. The networking model is bridge so the AI doesn't have access to my local network.

I have manually created the VM and provisioned like this:

** SSH into the server
#+BEGIN_SRC sh
ssh $server
#+END_SRC

** Create the cloud-init config
#+BEGIN_SRC sh :var PROJECT=/home/av/repos/haevas-n8n-infra/cloud-init-test/arch :session hs1ai :results raw drawer
$ cat <<EOF > $PROJECT/user-config
#cloud-config
hostname: base
manage_etc_hosts: true

users:
  - default
  - name: root
    lock_passwd: false
    ssh_authorized_keys:
      - ssh-rsa AAAA...
  - name: av
    lock_passwd: false
    plain_text_passwd: changeme
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: wheel
    ssh_authorized_keys:
      - ssh-rsa AAAA...

ssh_pwauth: true
disable_root: false

packages:
  - ansible
  - emacs
  - git
  - networkmanager
  - openssh
  - python
  - rsync
  - sudo
  - tmux
  - vim

runcmd:
  - systemctl enable --now sshd
  - systemctl enable --now NetworkManager
  - btrfs filesystem resize max /
EOF
#+END_SRC

Create the image
#+BEGIN_SRC sh :results raw drawer
xorriso -as genisoimage \
  -output cloud-init.iso \
  -volid CIDATA \
  -joliet -rock \
  cloud-init/user-data cloud-init/meta-data
sudo mv cloud-init.iso /var/lib/libvirt/images/
sudo chown libvirt-qemu:libvirt-qemu /var/lib/libvirt/images/cloud-init.iso
#+END_SRC

** Create the VM
Download the image
#+BEGIN_SRC sh :dir /hs1:/etc :results raw drawer
cd /var/lib/libvirt/images
sudo curl -LO https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso
#+END_SRC

If you need to delete the VM (and disk):
#+BEGIN_SRC sh :dir /hs1:/etc :results raw drawer
sudo virsh destroy code01 2>/dev/null || true
sudo virsh undefine code01 --remove-all-storage
#+END_SRC

Create the disk
#+BEGIN_SRC sh :dir /hs1:/etc :results raw drawer
sudo qemu-img create \
  -f qcow2 \
  -F qcow2 \
  -b /var/lib/libvirt/images/Arch-Linux-x86_64-cloudimg.qcow2 \
  /var/lib/libvirt/images/code01.qcow2
sudo qemu-img resize /var/lib/libvirt/images/code01.qcow2 20G
#+END_SRC


#+BEGIN_SRC sh :dir /hs1:/etc :results raw drawer
sudo virt-install \
  --name code01 \
  --memory 8192 \
  --vcpus 2 \
  --cpu host-model \
  --os-variant archlinux \
  --import \
  --disk path=/var/lib/libvirt/images/code01.qcow2,format=qcow2,bus=virtio \
  --disk path=/var/lib/libvirt/images/cloud-init.iso,device=cdrom \
  --network network=default,model=virtio,mac=52:54:00:5c:ad:9c \
  --graphics vnc,listen=127.0.0.1
  --console pty,target_type=serial \
  --noautoconsole
sudo virsh autostart code01
#+END_SRC

The goal of this project is be able to replicate a similar architecture but with some extra features.

I would like to be able to create both VM's and podman containers using vagrant. And also provision them using ansible.

Here is an example:
> ls -ls ~/repos/
total 0
0 drwxr-xr-x 1 av av 256 Dec 28 13:59 project1/
0 drwxr-xr-x 1 av av   6 Dec 28 23:27 project2/
0 drwxr-xr-x 1 av av   6 Dec 28 23:27 project3/
0 drwxr-xr-x 1 av av 176 Dec 29 01:21 project4/

All the projects reside in this main folder.

The goal is that when I cd into a folder, I can have the configuration of the VM in a .env file, type of infra (VM or container), RAM size, number of processors, port forwarding, etc. Then on that project directory I can use vagrant with some extra scripts/wrappers so I can use this CLI API:
- $WRAPPER up
- $WRAPPER ssh
- $WRAPPER stop
- $WRAPPER rm

Where wrapper could be a fabric/invoke wrapper (preferred) or a makefile.

The core idea is that this project is a master-template, so I don't have to create Vagrantfiles on each project folder individually. Similar to "tmuxp load .", hence the name of this project.

Maybe it is possible to use the principles equivalent to this in bash: BASENAME="$(basename "$PWD")" / PWD="$(pwd)" ""

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Manage VM Infrastructure (Priority: P1)

A developer wants to create a virtual machine for their project without manually writing Vagrantfiles or running complex commands. They create a .env configuration file in their project directory with VM settings and use simple wrapper commands to manage the VM lifecycle.

**Why this priority**: This is the core functionality - without it, users cannot use the system at all. It directly addresses the user's manual VM creation pain point.

**Independent Test**: Can create a VM from .env config, verify it runs, SSH into it, and remove it - delivering complete infrastructure management in isolation.

**Acceptance Scenarios**:

1. **Given** a project directory with a valid .env file specifying VM settings, **When** the user runs `$WRAPPER up`, **Then** a VM is created with the specified resources and becomes reachable
2. **Given** a running VM, **When** the user runs `$WRAPPER ssh`, **Then** the user is connected to the VM shell with appropriate credentials
3. **Given** a running VM, **When** the user runs `$WRAPPER stop`, **Then** the VM stops gracefully without data loss
4. **Given** a stopped VM, **When** the user runs `$WRAPPER rm`, **Then** the VM and all its resources are completely removed
5. **Given** an invalid .env configuration, **When** the user runs `$WRAPPER up`, **Then** the system displays clear error messages without creating any infrastructure

---

### User Story 2 - Create and Manage Container Infrastructure (Priority: P2)

A developer wants to create a lightweight container environment for their project. They use the same .env-based configuration but specify container infrastructure instead of a VM.

**Why this priority**: Extends system capabilities beyond VMs, important for modern containerized workloads but secondary to core VM functionality.

**Independent Test**: Can create a container from .env config, verify it runs, SSH into it, and remove it - delivering container management without VM dependencies.

**Acceptance Scenarios**:

1. **Given** a project directory with a .env file specifying container infrastructure, **When** the user runs `$WRAPPER up`, **Then** a Podman container is created with the specified configuration
2. **Given** a running container, **When** the user runs `$WRAPPER ssh`, **Then** the user is connected to the container shell
3. **Given** a running container, **When** the user runs `$WRAPPER stop`, **Then** the container stops gracefully
4. **Given** a stopped container, **When** the user runs `$WRAPPER rm`, **Then** the container and its resources are removed

---

### User Story 3 - Configure Infrastructure Resources (Priority: P3)

A developer needs to customize infrastructure resources like memory, CPU, disk size, and network settings for their specific project requirements.

**Why this priority**: Configuration is essential for flexibility but can use reasonable defaults initially.

**Independent Test**: Can create VMs/containers with different resource configurations and verify they match the .env specification.

**Acceptance Scenarios**:

1. **Given** a .env file specifying custom RAM (e.g., 16GB), **When** infrastructure is created, **Then** it has exactly 16GB of RAM allocated
2. **Given** a .env file specifying 4 CPUs, **When** infrastructure is created, **Then** it has 4 CPU cores available
3. **Given** a .env file specifying port forwarding rules, **When** infrastructure is created, **Then** the specified ports are accessible from the host
4. **Given** a .env file specifying network type (e.g., bridge), **When** infrastructure is created, **Then** networking is configured according to the specification

---

### User Story 4 - Provision Infrastructure Automatically (Priority: P3)

A developer wants to automatically install software and configure their infrastructure after creation using automated configuration scripts.

**Why this priority**: Automation is important for productivity but infrastructure creation is the primary requirement.

**Independent Test**: Can create infrastructure and verify that automated provisioning runs and applies the specified configuration.

**Acceptance Scenarios**:

1. **Given** a .env file specifying a provisioning script path, **When** `$WRAPPER up` completes, **Then** the provisioning script has been executed on the infrastructure
2. **Given** a provisioning script that installs software, **When** infrastructure is provisioned, **Then** the specified software is installed and functional
3. **Given** a provisioning script execution failure, **When** provisioning fails, **Then** the system provides clear error messages showing the failure point

---

### User Story 5 - Validate Configuration Before Deployment (Priority: P3)

A developer wants to ensure their .env configuration is valid before creating infrastructure to avoid wasted time on failed deployments.

**Why this priority**: Validation improves user experience but doesn't block basic functionality.

**Independent Test**: Can run validation on various .env files and receive accurate feedback about validity issues.

**Acceptance Scenarios**:

1. **Given** a valid .env configuration, **When** validation runs, **Then** the system confirms the configuration is valid
2. **Given** an invalid .env configuration (e.g., negative RAM value), **When** validation runs, **Then** the system identifies the specific error and provides guidance
3. **Given** a .env file with missing required fields, **When** validation runs, **Then** the system lists all missing required fields

---

### Edge Cases

- What happens when the user tries to create infrastructure for a project that already has running infrastructure?
- What happens when the user runs `$WRAPPER rm` on infrastructure that doesn't exist?
- How does the system handle conflicts with existing VM/container names on the host?
- What happens when there's insufficient disk space or memory on the host?
- How does the system handle network conflicts (e.g., port already in use)?
- What happens when the .env file is missing or unreadable?
- How does the system handle interruption of long-running operations (e.g., user presses Ctrl+C during `$WRAPPER up`)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support creating virtual machine infrastructure from a .env configuration file in the current project directory
- **FR-002**: System MUST support creating Podman container infrastructure from a .env configuration file in the current project directory
- **FR-003**: System MUST allow users to configure infrastructure resources including RAM size, CPU count, disk size, and networking settings via .env file
- **FR-004**: System MUST provide a wrapper command interface with subcommands: up, ssh, stop, and rm
- **FR-005**: System MUST use the project directory name as the default identifier for infrastructure instances, with Vagrant's automatic hash/number suffixing handling naming conflicts
- **FR-006**: System MUST use the project directory path as the default context for locating configuration files
- **FR-007**: System MUST support automated provisioning script execution for infrastructure configuration after creation
- **FR-008**: System MUST provide SSH access to created infrastructure via the wrapper ssh command
- **FR-009**: System MUST validate .env configuration files before creating infrastructure
- **FR-010**: System MUST display clear error messages when configuration is invalid or infrastructure creation fails
- **FR-011**: System MUST support stopping and removing infrastructure without affecting other projects
- **FR-012**: System MUST not require users to create or maintain individual infrastructure definition files for each project
- **FR-013**: System MUST automatically read infrastructure configuration from the current project directory when wrapper commands are executed
- **FR-014**: System MUST support fixed IP assignment for infrastructure when configured
- **FR-015**: System MUST support port forwarding configuration for infrastructure
- **FR-016**: System MUST provide idempotent infrastructure operations (running `$WRAPPER up` multiple times on the same project should not create duplicate infrastructure)
- **FR-017**: System MUST support both bridge and default networking modes
- **FR-018**: System MUST automatically assign a unique name to infrastructure if not specified in .env, leveraging Vagrant's built-in naming conflict resolution with hash/number suffixes
- **FR-019**: System MUST allow users to specify custom provisioning scripts/playbooks via .env configuration
- **FR-020**: System MUST provide clear status feedback for all wrapper operations
- **FR-021**: System MUST measure and log performance metrics for all operations (creation time, connection time, stop time, remove time) for documentation purposes

## Clarifications

### Session 2025-12-29

- Q: Configuration File Schema Definition → A: Simple flat key-value format (KEY=value) with required fields: INFRA_TYPE (vm|container), MEMORY (MB), CPUS (integer), DISK (GB). Optional: NETWORK_TYPE, PORTS, PROVISION_SCRIPT.
- Q: Naming Conflict Resolution → A: Vagrant handles this automatically by adding hash/number suffix to VM names, preventing collisions.
- Q: Scalability Limits and Resource Management → A: No limits - rely on host OS cgroup isolation and kernel resource management.
- Q: Out-of-Scope Features → A: Exclude multi-host orchestration, GUI/visual management interface, automated scaling/auto-scaling infrastructure, infrastructure monitoring dashboards, advanced security features (RBAC, audit logging beyond basic access).
- Q: Performance Metrics and Target Times → A: No specific targets - only measure and document actual times.

### Key Entities

- **Project Directory**: A folder containing a configuration file that defines infrastructure requirements. The directory name serves as the default infrastructure identifier.
- **Infrastructure Instance**: A running virtual machine or container created from a project directory's configuration. Each instance has unique resources, networking, and state.
- **Configuration File (.env)**: A flat key-value format file (KEY=value) in the project directory containing infrastructure type, resources, networking, and provisioning settings. Required fields: `INFRA_TYPE` (vm|container), `MEMORY` (integer in MB), `CPUS` (integer), `DISK` (integer in GB). Optional fields: `NETWORK_TYPE` (bridge|default), `PORTS` (comma-separated port forwarding rules), `PROVISION_SCRIPT` (path to Ansible playbook or script), `FIXED_IP` (IP address string).
- **Wrapper Command**: A command-line interface that provides up, ssh, stop, and rm subcommands for infrastructure management.
- **Provisioning Script**: An automated configuration script specified in the configuration file that runs automatically after infrastructure creation to install and configure software.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a new project with configured infrastructure efficiently (system will measure and document actual creation times without pre-defined targets)
- **SC-002**: Users can switch between multiple projects and manage their infrastructure independently without conflicts
- **SC-003**: 100% of infrastructure operations (up, ssh, stop, rm) complete successfully when using valid configurations
- **SC-004**: System detects and reports 100% of configuration errors before attempting infrastructure creation
- **SC-005**: Users can provision a project with automated configuration scripts and have all software installed automatically without manual intervention
- **SC-006**: Infrastructure resources (RAM, CPU, disk) match the configuration file specification exactly in 100% of cases
- **SC-007**: Users can SSH into created infrastructure using a single command without remembering complex connection details
- **SC-008**: System prevents creation of duplicate infrastructure for the same project directory (idempotent operations)
- **SC-009**: Network settings (including port forwarding and fixed IPs) work correctly on first attempt in 95% of cases
- **SC-010**: Users can remove all infrastructure resources for a project with a single wrapper command

## Assumptions

- Users have necessary permissions to create VMs/containers on the host system
- Users have access to the base VM images and container images required for infrastructure creation
- The host system has a compatible virtualization provider available
- The host system has a container runtime installed for container support
- A configuration management system is available on the host system for provisioning operations
- Users are familiar with basic command-line operations
- SSH keys are set up for infrastructure access or passwords can be provided in configuration
- The network bridge interface exists on the host system for bridge networking mode
- Sufficient system resources (disk, RAM, CPU) are available for infrastructure creation
- Host OS cgroups and kernel resource management will handle resource isolation and allocation between concurrent infrastructure instances
- System will not enforce limits on concurrent projects or resource quotas, delegating resource contention management to the host OS

## Out of Scope

The following features are explicitly out of scope for this feature:

- **Multi-host orchestration**: System operates on a single host system only. No clustering or distributed infrastructure management.
- **GUI/visual management interface**: All interactions occur through command-line interface only.
- **Automated scaling/auto-scaling**: System does not automatically scale infrastructure up or down based on load or metrics.
- **Infrastructure monitoring dashboards**: No built-in monitoring, metrics visualization, or dashboards provided.
- **Advanced security features**: No role-based access control (RBAC), audit logging, or fine-grained authorization beyond basic SSH access.
- **Cloud provider integration**: No support for provisioning infrastructure on AWS, GCP, Azure, or other cloud platforms.
- **Infrastructure backup/restore**: No automated backup or disaster recovery functionality.
- **High availability clustering**: No support for active-active or active-passive configurations across multiple hosts.

## Dependencies

- Virtualization provider for VM support
- Container runtime for container support
- Configuration management system for automated provisioning
- SSH client for infrastructure access
- Network bridge interface (for bridge networking mode)
- Base operating system images for VM creation
- Base container images
