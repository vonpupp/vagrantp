# Ansible Playbook Examples

This directory contains example Ansible playbooks for use with Vagrantp.

## Examples

### `simple-service.yml`

Basic example that installs and starts Nginx web server.

### `user-management.yml`

Example that creates users and configures SSH access.

### `development-env.yml`

Example that installs development tools (Python, Node.js, etc.).

### `multi-distro.yml`

Example showing multi-distro support (Debian/Arch/RedHat).

## Usage

1. Copy an example playbook to your project:

```bash
cp examples/simple-service.yml playbooks/site.yml
```

2. Add to your `.env`:

```env
PROVISIONING_PLAYBOOK=./playbooks/site.yml
```

3. Run `vagrantp up`

## Default Playbook

Vagrantp includes a default playbook at `ansible/site.yml` in the project root that installs
base packages (git, vim, tmux, curl, wget). You can use it directly or copy
it as a template for custom playbooks.
