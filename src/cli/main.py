"""Main CLI entry point using Invoke framework."""

import sys
from pathlib import Path

from invoke.collection import Collection
from invoke.program import Program
from invoke.tasks import task

from config.parser import ConfigurationParser
from podman.container_manager import ContainerManager
from provision.ansible import AnsibleProvisioner
from utils.helpers import (
    ConfigInvalidError,
    ConfigNotFoundError,
    ErrorCode,
    InfrastructureExistsError,
    InfrastructureState,
    ProvisioningFailedError,
    VagrantpError,
)
from vagrant.vm_manager import VMManager


@task
def version(c):
    """Show version information."""
    print("Vagrantp 1.0.0")


@task
def up(c, dry_run=False, no_provision=False):
    """Create and start infrastructure."""
    try:
        parser = ConfigurationParser()
        config = parser.load()

        validation_result = parser.validate()
        if not validation_result.valid:
            print("✗ Configuration validation failed:")
            for error in validation_result.errors:
                print(f"  - {error}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        if dry_run:
            print("✓ Configuration validated")
            print(f"  INFRA_TYPE: {infra_type}")
            print(f"  PROVIDER: {config.get('PROVIDER')}")
            print(f"  ID: {infra_id}")
            return

        vm_manager = None
        container_manager = None
        manager = None

        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            manager = vm_manager
            container_manager = None
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)
            manager = container_manager
            vm_manager = None
        else:
            print(f"✗ Unknown INFRA_TYPE: {infra_type}")
            sys.exit(ErrorCode.CONFIG_ERROR.value)

        current_state = manager._get_state()

        if current_state != InfrastructureState.NOT_CREATED:
            if current_state == InfrastructureState.RUNNING:
                raise InfrastructureExistsError(infra_id, current_state.value)
            elif current_state == InfrastructureState.STOPPED:
                print("✓ Configuration validated")
                print("→ Starting stopped infrastructure...")
                print(f"  INFRA_TYPE: {infra_type}")
                print(f"  ID: {infra_id}")
                manager.start()

                if not no_provision and config.get("PROVISIONING_PLAYBOOK"):
                    provisioner = AnsibleProvisioner(infra_type=infra_type, infra_id=infra_id)
                    if provisioner.is_provisioned():
                        print("ℹ Provisioning already completed (skipping)")
                        print("  To re-provision, remove .provisioned marker file")
                        return

                    playbook_path = Path(config["PROVISIONING_PLAYBOOK"])
                    vars_path = (
                        Path(config["PROVISIONING_VARS"])
                        if config.get("PROVISIONING_VARS")
                        else None
                    )

                    inventory_path = infra_type
                    if infra_type == "vm" and vm_manager is not None:
                        inventory_path = vm_manager._get_ssh_host()
                    elif infra_type == "container" and container_manager is not None:
                        inventory_path = container_manager._get_ssh_host()

                    try:
                        provisioner.execute(
                            playbook_path=playbook_path,
                            inventory_path=inventory_path,
                            vars_path=vars_path,
                            dry_run=dry_run,
                        )
                    except ProvisioningFailedError as e:
                        print(f"✗ {e.message}")
                        if e.suggestion:
                            print(f"  → {e.suggestion}")
                        sys.exit(ErrorCode.PROVISIONING_FAILED.value)

                return
            else:
                print(f"ℹ Infrastructure '{infra_id}' exists in state: {current_state.value}")
                return

        print("✓ Configuration validated")
        print("→ Starting infrastructure...")
        print(f"  INFRA_TYPE: {infra_type}")
        if infra_type == "vm":
            print(f"  PROVIDER: {config.get('PROVIDER')}")
        else:
            print(f"  IMAGE: {config.get('IMAGE', 'alpine:latest')}")
        print(f"  ID: {infra_id}")

        if infra_type == "vm" and vm_manager is not None:
            vm_manager.create(config)
        elif infra_type == "container" and container_manager is not None:
            container_manager.create(config)

        if not no_provision and config.get("PROVISIONING_PLAYBOOK"):
            provisioner = AnsibleProvisioner(infra_type=infra_type, infra_id=infra_id)
            if provisioner.is_provisioned():
                print("ℹ Provisioning already completed (skipping)")
                print("  To re-provision, remove .provisioned marker file")
                return

            playbook_path = Path(config["PROVISIONING_PLAYBOOK"])
            vars_path = (
                Path(config["PROVISIONING_VARS"]) if config.get("PROVISIONING_VARS") else None
            )

            inventory_path = infra_type
            if infra_type == "vm" and vm_manager is not None:
                inventory_path = vm_manager._get_ssh_host()
            elif infra_type == "container" and container_manager is not None:
                inventory_path = container_manager._get_ssh_host()

            try:
                provisioner.execute(
                    playbook_path=playbook_path,
                    inventory_path=inventory_path,
                    vars_path=vars_path,
                    dry_run=dry_run,
                )
            except ProvisioningFailedError as e:
                print(f"✗ {e.message}")
                if e.suggestion:
                    print(f"  → {e.suggestion}")
                sys.exit(ErrorCode.PROVISIONING_FAILED.value)

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
    """Connect to infrastructure."""
    try:
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

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


@task
def stop(c, force=False):
    """Stop infrastructure."""
    try:
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

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


@task
def rm(c, force=False):
    """Remove infrastructure."""
    try:
        parser = ConfigurationParser()
        config = parser.load()

        infra_type = config.get("INFRA_TYPE", "vm")
        infra_id = config.get("INFRA_ID", Path.cwd().name)

        if infra_type == "vm":
            vm_manager = VMManager(infra_id)

            if not force:
                state = vm_manager._get_state()
                if state != InfrastructureState.NOT_CREATED:
                    print(f"⚠ Warning: This will permanently remove infrastructure '{infra_id}'")
                    response = input("→ Type 'yes' to confirm: ")
                    if response.lower() != "yes":
                        print("✗ Removal cancelled")
                        return

            vm_manager.remove(force)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)

            if not force:
                state = container_manager._get_state()
                if state != InfrastructureState.NOT_CREATED:
                    print(f"⚠ Warning: This will permanently remove infrastructure '{infra_id}'")
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


# Create program directly with namespace
program = Program(namespace=Collection.from_module(sys.modules[__name__]), version="1.0.0")


if __name__ == "__main__":
    program.run()
