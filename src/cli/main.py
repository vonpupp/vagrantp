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


@task
def up(c, dry_run=False, no_provision=False):
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
        print(f"  PROVIDER: {config.get('PROVIDER')}")
        print(f"  ID: {infra_id}")

        # Create infrastructure based on type
        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            vm_manager.create(config)
        else:
            print(f"ℹ Container infrastructure not yet implemented")
            print("  This will be implemented in Phase 4")

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


@task
def ssh(c, command=None):
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
        else:
            print(f"ℹ Container infrastructure not yet implemented")
            print("  This will be implemented in Phase 4")

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


@task
def stop(c, force=False):
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
        else:
            print(f"ℹ Container infrastructure not yet implemented")
            print("  This will be implemented in Phase 4")

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


@task
def rm(c, force=False):
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
        else:
            print(f"ℹ Container infrastructure not yet implemented")
            print("  This will be implemented in Phase 4")

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


@task
def ssh(c, command=None):
    """Connect to infrastructure.

    Args:
        c: Invoke context.
        command: Execute single command and exit.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        # Get infrastructure ID
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Check infrastructure state
        state_manager = StateManager()
        current_state = state_manager.get_state(infra_id)

        if current_state != InfrastructureState.RUNNING:
            print(
                f"✗ Infrastructure '{infra_id}' is not running (state: {current_state.value})"
            )
            print("  → Run 'vagrantp up' to start the infrastructure")
            sys.exit(ErrorCode.GENERAL_ERROR.value)

        print(f"ℹ SSH connection to '{infra_id}'")
        if command:
            print(f"  Command: {command}")
        else:
            print("  Interactive shell")

        # TODO: Implement SSH connection
        print("ℹ SSH connection not yet implemented")
        print("  This is a placeholder for Phase 3 implementation")

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


@task
def stop(c, force=False):
    """Stop infrastructure.

    Args:
        c: Invoke context.
        force: Force stop without graceful shutdown.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        # Get infrastructure ID
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Check infrastructure state
        state_manager = StateManager()
        current_state = state_manager.get_state(infra_id)

        if current_state == InfrastructureState.NOT_CREATED:
            print(f"ℹ Infrastructure '{infra_id}' does not exist")
            print("  → No action needed")
            return

        if current_state != InfrastructureState.RUNNING:
            print(
                f"ℹ Infrastructure '{infra_id}' is not running (state: {current_state.value})"
            )
            print("  → No action needed")
            return

        print(f"ℹ Stopping infrastructure '{infra_id}'")
        if force:
            print("  Force stop enabled")

        # TODO: Implement infrastructure stop
        print("ℹ Infrastructure stop not yet implemented")
        print("  This is a placeholder for Phase 3 implementation")

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


@task
def rm(c, force=False):
    """Remove infrastructure.

    Args:
        c: Invoke context.
        force: Force removal without stopping first.
    """
    try:
        # Load configuration
        parser = ConfigurationParser()
        config = parser.load()

        # Get infrastructure ID
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        # Check infrastructure state
        state_manager = StateManager()
        current_state = state_manager.get_state(infra_id)

        if current_state == InfrastructureState.NOT_CREATED:
            print(f"ℹ Infrastructure '{infra_id}' does not exist")
            print("  → No action needed")
            return

        print(f"⚠ Warning: This will permanently remove infrastructure '{infra_id}'")

        if not force:
            # Confirmation prompt
            response = input("→ Type 'yes' to confirm: ")
            if response.lower() != "yes":
                print("✗ Removal cancelled")
                return

        if current_state == InfrastructureState.RUNNING:
            print("  Stopping infrastructure first...")
            # TODO: Implement stop

        print("  Cleaning up resources...")

        # TODO: Implement infrastructure removal
        print("ℹ Infrastructure removal not yet implemented")
        print("  This is a placeholder for Phase 3 implementation")

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
ns.configure({"tasks": [up, ssh, stop, rm]})

# Create program instance
program = Program(namespace=ns, version="1.0.0")


if __name__ == "__main__":
    program.run()
