"""Main CLI entry point using Invoke framework."""

import sys
from pathlib import Path
from invoke.tasks import task
from invoke.program import Program
from invoke.collection import Collection

from config.parser import ConfigurationParser, ValidationError
from utils.helpers import (
    VagrantpError,
    ConfigNotFoundError,
    ConfigInvalidError,
    InfrastructureExistsError,
    ErrorCode,
    InfrastructureState,
    StateManager,
)
from vagrant.vm_manager import VMManager
from podman.container_manager import ContainerManager


@task
def show_version(c):
    """Show version information."""
    print("Vagrantp 1.0.0")


@task(name="up")
def up_task(c, dry_run=False, no_provision=False):
    """Create and start infrastructure.

    Args:
        c: Invoke context.
        dry_run: Validate configuration without creating infrastructure.
        no_provision: Skip provisioning step.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        # Validate configuration
        validation_result = parser.validate()
        if not validation_result.valid:
            print("✗ Configuration validation failed:")
            for error in validation_result.errors:
                print(f"  - {error}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

        infra_type = config.get("INFRA_TYPE", "vm")

        if dry_run:
            print("✓ Configuration validated")
            print(f"  INFRA_TYPE: {infra_type}")
            print(f"  PROVIDER: {config.get('PROVIDER')}")
            return

        # Get infrastructure ID
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Check if infrastructure already exists
        state_manager = StateManager()
        current_state = state_manager.get_state(infra_id)

        if current_state != InfrastructureState.NOT_CREATED:
            if current_state == InfrastructureState.RUNNING:
                raise InfrastructureExistsError(infra_id, current_state.value)
            else:
                print(
                    f"ℹ Infrastructure '{infra_id}' exists in state: {current_state.value}"
                )
                print("  Run 'vagrantp up' to start, or 'vagrantp rm' to recreate")
                return

        print("✓ Configuration validated")
        print("→ Starting infrastructure...")
        print(f"  INFRA_TYPE: {infra_type}")
        if infra_type == "vm":
            print(f"  PROVIDER: {config.get('PROVIDER')}")
        else:
            print(f"  IMAGE: {config.get('IMAGE', 'alpine:latest')}")
        print(f"  ID: {infra_id}")

        # Create infrastructure based on type
        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            vm_manager.create(config)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)
            container_manager.create(config)
        else:
            print(f"✗ Unknown INFRA_TYPE: {infra_type}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

        # TODO: Implement provisioning
        if not no_provision and config.get("PROVISIONING_PLAYBOOK"):
            print("ℹ Provisioning not yet implemented")
            print("  This will be implemented in Phase 6")

    except ConfigNotFoundError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(ErrorCode.CONFIG_ERROR.value)
    except ConfigInvalidError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(ErrorCode.CONFIG_ERROR.value)
    except VagrantpError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(e.code.value)


@task(name="ssh")
def ssh_task(c, command=None):
    """Connect to infrastructure.

    Args:
        c: Invoke context.
        command: Execute single command and exit.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Connect to infrastructure based on type
        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            vm_manager.connect(command)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)
            container_manager.connect(command)
        else:
            print(f"✗ Unknown INFRA_TYPE: {infra_type}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

    except ConfigNotFoundError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(ErrorCode.CONFIG_ERROR.value)
    except VagrantpError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(e.code.value)


@task(name="stop")
def stop_task(c, force=False):
    """Stop infrastructure.

    Args:
        c: Invoke context.
        force: Force stop without graceful shutdown.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Stop infrastructure based on type
        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            vm_manager.stop(force)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)
            container_manager.stop(force)
        else:
            print(f"✗ Unknown INFRA_TYPE: {infra_type}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

    except ConfigNotFoundError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(ErrorCode.CONFIG_ERROR.value)
    except VagrantpError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(e.code.value)


@task(name="rm")
def rm_task(c, force=False):
    """Remove infrastructure.

    Args:
        c: Invoke context.
        force: Force removal without stopping first.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Remove infrastructure based on type
        if infra_type == "vm":
            vm_manager = VMManager(infra_id)

            if not force:
                state = vm_manager.state_manager.get_state(infra_id)
                if state != InfrastructureState.NOT_CREATED:
                    print(
                        f"⚠ Warning: This will permanently remove infrastructure '{infra_id}'"
                    )
                    response = input("→ Type 'yes' to confirm: ")
                    if response.lower() != "yes":
                        print("✗ Removal cancelled")
                        return

            vm_manager.remove(force)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)

            if not force:
                state = container_manager.state_manager.get_state(infra_id)
                if state != InfrastructureState.NOT_CREATED:
                    print(
                        f"⚠ Warning: This will permanently remove infrastructure '{infra_id}'"
                    )
                    response = input("→ Type 'yes' to confirm: ")
                    if response.lower() != "yes":
                        print("✗ Removal cancelled")
                        return

            container_manager.remove(force)
        else:
            print(f"✗ Unknown INFRA_TYPE: {infra_type}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

    except ConfigNotFoundError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(ErrorCode.CONFIG_ERROR.value)
    except VagrantpError as e:
        print(f"✗ {e.message}")
        if e.suggestion:
            print(f"  → {e.suggestion}")
        sys.exit(e.code.value)


# Create collection of tasks
ns = Collection()
ns.configure({"tasks": [show_version, up_task, ssh_task, stop_task, rm_task]})

# Create program instance
program = Program(namespace=ns, version="1.0.0")


if __name__ == "__main__":
    program.run()
