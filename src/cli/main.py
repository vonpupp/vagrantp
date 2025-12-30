"""Main CLI entry point using Invoke framework."""

import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from invoke.collection import Collection
from invoke.program import Program
from invoke.tasks import task

from config.parser import ConfigurationParser
from podman.container_manager import ContainerManager
from provision.ansible import ProvisioningFailedError, ProvisioningManager
from utils.helpers import (
    ConfigInvalidError,
    ConfigNotFoundError,
    ErrorCode,
    InfrastructureExistsError,
    InfrastructureState,
    VagrantpError,
    run_command,
)
from vagrant.vm_manager import VMManager

_PLAYBOOK_TEMP_DIR = f"{tempfile.gettempdir()}/vagrantp_playbooks_{uuid.uuid4().hex[:8]}"


@task
def version(c):
    """Show version information."""
    print("Vagrantp 1.0.0")


def _detect_container_runtime() -> str | None:
    """Detect container runtime (docker or podman).

    Returns:
        Runtime name ('podman', 'docker', or None if neither found).
    """
    try:
        run_command(["podman", "--version"], check=False)
        return "podman"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        run_command(["docker", "--version"], check=False)
        return "docker"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def _check_ansible_in_container(runtime: str, container_id: str) -> bool:
    """Check if Ansible is installed in container.

    Args:
        runtime: Container runtime ('podman' or 'docker').
        container_id: Container name or ID.

    Returns:
        True if Ansible is installed, False otherwise.
    """
    try:
        result = run_command([runtime, "exec", container_id, "which", "ansible"], check=False)
        # Check if which found ansible (exit code 0 and output not empty)
        return result.returncode == 0 and "ansible" in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install_python_in_container(runtime: str, container_id: str) -> bool:
    """Install Python in container if not present.

    Args:
        runtime: Container runtime ('podman' or 'docker').
        container_id: Container name or ID.

    Returns:
        True if Python is now available, False otherwise.
    """
    try:
        result = run_command([runtime, "exec", container_id, "which", "python3"], check=False)
        if result.returncode == 0:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        print("  → Installing Python in container...")
        subprocess.run(
            [runtime, "exec", container_id, "pacman", "-Sy", "--noconfirm", "python"],
            check=True,
            capture_output=True,
        )
        print("  ✓ Python installed")
        return True
    except subprocess.CalledProcessError:
        try:
            subprocess.run(
                [runtime, "exec", container_id, "apk", "add", "--no-cache", "python3"],
                check=True,
                capture_output=True,
            )
            print("  ✓ Python installed")
            return True
        except subprocess.CalledProcessError:
            try:
                subprocess.run(
                    [runtime, "exec", container_id, "apt-get", "update", "-qq"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [runtime, "exec", container_id, "apt-get", "install", "-y", "python3"],
                    check=True,
                    capture_output=True,
                )
                print("  ✓ Python installed")
                return True
            except subprocess.CalledProcessError:
                print("  ✗ Failed to install Python")
                return False


def _install_ansible_in_container(runtime: str, container_id: str) -> bool:
    """Install Ansible in container if not present.

    Args:
        runtime: Container runtime ('podman' or 'docker').
        container_id: Container name or ID.

    Returns:
        True if Ansible is now available, False otherwise.
    """
    try:
        result = run_command([runtime, "exec", container_id, "which", "ansible"], check=False)
        if result.returncode == 0:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("  → Installing Ansible in container...")
    try:
        subprocess.run(
            [runtime, "exec", container_id, "pacman", "-Sy", "--noconfirm", "ansible"],
            check=True,
            capture_output=True,
        )
        print("  ✓ Ansible installed")
        return True
    except subprocess.CalledProcessError:
        try:
            subprocess.run(
                [runtime, "exec", container_id, "apk", "add", "--no-cache", "ansible"],
                check=True,
                capture_output=True,
            )
            print("  ✓ Ansible installed")
            return True
        except subprocess.CalledProcessError:
            try:
                subprocess.run(
                    [runtime, "exec", container_id, "apt-get", "update", "-qq"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [runtime, "exec", container_id, "apt-get", "install", "-y", "ansible"],
                    check=True,
                    capture_output=True,
                )
                print("  ✓ Ansible installed")
                return True
            except subprocess.CalledProcessError:
                print("  ✗ Failed to install Ansible")
                return False


def _copy_playbook_to_container(runtime: str, container_id: str, playbook_path: Path) -> None:
    """Copy playbook file/directory into container.

    Args:
        runtime: Container runtime ('podman' or 'docker').
        container_id: Container name or ID.
        playbook_path: Path to playbook on host.
    """
    project_dir = Path.cwd()

    if playbook_path.is_absolute():
        playbook_rel = playbook_path.relative_to(project_dir)
    else:
        playbook_rel = playbook_path

    playbook_dir_host = project_dir / playbook_rel
    if not playbook_dir_host.exists():
        raise FileNotFoundError(f"Playbook not found: {playbook_dir_host}")

    # Create target directory in container
    mkdir_cmd = [runtime, "exec", container_id, "mkdir", "-p", _PLAYBOOK_TEMP_DIR]
    subprocess.run(mkdir_cmd, cwd=project_dir, check=True)

    # Copy playbook directory into container
    copy_cmd = [
        runtime,
        "cp",
        str(playbook_dir_host),
        f"{container_id}:{_PLAYBOOK_TEMP_DIR}/",
    ]
    subprocess.run(copy_cmd, cwd=project_dir, check=True)


def _run_container_playbook(
    runtime: str, container_id: str, playbook: str, extra_vars: str | None
) -> None:
    """Run Ansible playbook inside container.

    Args:
        runtime: Container runtime ('podman' or 'docker').
        container_id: Container name or ID.
        playbook: Path to playbook (relative to project dir).
        extra_vars: Extra variables for playbook.
    """
    project_dir = Path.cwd()

    # Copy playbook files into container
    playbook_path_host = Path(playbook)
    if playbook_path_host.is_absolute():
        playbook_rel = playbook_path_host.relative_to(project_dir)
    else:
        playbook_rel = playbook_path_host

    playbook_dir_host = project_dir / playbook_rel
    if not playbook_dir_host.exists():
        raise FileNotFoundError(f"Playbook not found: {playbook_dir_host}")

    # Create target directory in container
    mkdir_cmd = [runtime, "exec", container_id, "mkdir", "-p", _PLAYBOOK_TEMP_DIR]
    subprocess.run(mkdir_cmd, cwd=project_dir, check=True)

    # Copy playbook directory into container
    copy_cmd = [
        runtime,
        "cp",
        str(playbook_dir_host),
        f"{container_id}:{_PLAYBOOK_TEMP_DIR}/",
    ]
    subprocess.run(copy_cmd, cwd=project_dir, check=True)

    # Build extra vars arg
    extra_vars_arg = ""
    if extra_vars:
        # Check if extra_vars is a file path
        if Path(extra_vars).exists():
            # Copy extra-vars file to container
            vars_file_host = project_dir / Path(extra_vars)
            if vars_file_host.exists():
                copy_vars_cmd = [
                    runtime,
                    "cp",
                    str(vars_file_host),
                    f"{container_id}:{_PLAYBOOK_TEMP_DIR}/",
                ]
                subprocess.run(copy_vars_cmd, cwd=project_dir, check=True)
            extra_vars_arg = f"--extra-vars '@{Path(extra_vars).name}'"
        else:
            extra_vars_arg = f"--extra-vars '{extra_vars}'"

    # Execute ansible-playbook inside container
    cmd = [
        runtime,
        "exec",
        container_id,
        "sh",
        "-c",
        f"cd {_PLAYBOOK_TEMP_DIR} && ansible-playbook {Path(playbook_rel).name} -i default, -e 'ansible_host=localhost ansible_connection=local' {extra_vars_arg}",
    ]

    try:
        start_time = time.time()

        process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if process.stdout:
            for line in process.stdout:
                print(line, end="")

        returncode = process.wait()
        duration = time.time() - start_time

        if returncode != 0:
            raise ProvisioningFailedError(f"Playbook execution failed with exit code {returncode}")

        print(f"✓ Provisioning completed ({duration:.1f}s)")

    except subprocess.CalledProcessError as e:
        raise ProvisioningFailedError(f"Playbook execution failed: {e}")


def _run_provisioning(infra_id: str, config: dict, infra_type: str) -> None:
    """Run Ansible provisioning.

    Args:
        infra_id: Infrastructure identifier.
        config: Configuration dictionary.
        infra_type: Infrastructure type (vm or container).

    Raises:
        VagrantpError: If provisioning fails.
    """
    playbook = config.get("PROVISIONING_PLAYBOOK")
    if not playbook:
        print("ℹ No playbook specified (skipping provisioning)")
        return

    extra_vars = config.get("PROVISIONING_VARS")
    ssh_user = config.get("SSH_USER")
    ssh_key = config.get("SSH_KEY")
    auto_install_ansible = config.get("PROVISIONING_AUTO_INSTALL_ANSIBLE", "false").lower() in [
        "true",
        "1",
        "yes",
    ]

    provision_manager = ProvisioningManager(infra_id)

    # Check if already provisioned
    if provision_manager.check_provisioning_status():
        print("ℹ Infrastructure already provisioned (skipping)")
        print("  Run 'vagrantp rm' then 'vagrantp up' to reprovision")
        return

    # Build inventory string based on infra type
    inventory = None
    runtime = None
    if infra_type == "vm":
        # For VMs, use Vagrant's SSH config
        # Vagrant sets up SSH config automatically
        inventory = "default"
    elif infra_type == "container":
        # For containers, detect runtime and check ansible
        container_manager = ContainerManager(infra_id)
        state = container_manager._get_state()
        if state != InfrastructureState.RUNNING:
            raise VagrantpError(
                f"Container is not running (state: {state.value})",
                ErrorCode.GENERAL_ERROR,
            )

        # Detect container runtime
        runtime = _detect_container_runtime()
        if not runtime:
            raise VagrantpError(
                "Neither Podman nor Docker detected",
                ErrorCode.GENERAL_ERROR,
                suggestion="Install Podman or Docker to use container provisioning",
            )

        # Check if ansible is installed in container
        if not _check_ansible_in_container(runtime, infra_id):
            if auto_install_ansible:
                print("→ Ansible not installed in container, auto-installing...")

                # First ensure Python is installed
                if not _install_python_in_container(runtime, infra_id):
                    print("✗ Failed to install Python in container")
                    print("  Skipping provisioning")
                    return

                # Install Ansible directly using package manager
                if not _install_ansible_in_container(runtime, infra_id):
                    print("✗ Failed to install Ansible in container")
                    print("  Skipping provisioning")
                    return
            else:
                print("ℹ Ansible not installed in container")
                print("  Skipping provisioning")
                print("  To enable auto-install, set PROVISIONING_AUTO_INSTALL_ANSIBLE=true")
                print("  Or use an image with Ansible pre-installed")
                return

    # Verify SSH connection before provisioning (for VMs only)
    if infra_type == "vm":
        try:
            result = run_command(["vagrant", "ssh-config"], check=False)
            if result.returncode == 0:
                provision_manager.verify_ssh_connection(
                    "default",
                    ssh_user=ssh_user,
                    ssh_key=ssh_key,
                )
        except (subprocess.CalledProcessError, OSError):
            pass  # SSH verification is optional, don't fail if it doesn't work

    try:
        # For containers, run ansible-playbook via runtime exec
        if infra_type == "container":
            if not runtime:
                raise VagrantpError(
                    "Container runtime not detected",
                    ErrorCode.GENERAL_ERROR,
                    suggestion="Ensure Podman or Docker is installed and running",
                )

            _run_container_playbook(runtime, infra_id, playbook, extra_vars)
        else:
            # For VMs, use regular ansible execution
            provision_manager.execute(
                playbook_path=playbook,
                inventory=inventory,
                extra_vars=extra_vars,
                dry_run=False,
                ssh_user=ssh_user,
                ssh_key=ssh_key,
                use_connection="ssh",
            )

        # Mark as provisioned
        provision_manager.mark_provisioned()
    except VagrantpError as e:
        # Re-raise with proper error code
        raise e
    except Exception as e:
        # Wrap unexpected errors
        raise VagrantpError(
            f"Provisioning failed: {e}",
            ErrorCode.PROVISIONING_FAILED,
            suggestion="Check playbook syntax and execution logs",
        )


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

        if dry_run:
            print("✓ Configuration validated")
            print(f"  INFRA_TYPE: {infra_type}")
            print(f"  PROVIDER: {config.get('PROVIDER')}")
            return

        infra_id = config.get("INFRA_ID", Path.cwd().name)

        if infra_type == "vm":
            manager = VMManager(infra_id)
        elif infra_type == "container":
            manager = ContainerManager(infra_id)
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
                    _run_provisioning(infra_id, config, infra_type)

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

        if infra_type == "vm":
            vm_manager = VMManager(infra_id)
            vm_manager.create(config)
        elif infra_type == "container":
            container_manager = ContainerManager(infra_id)
            container_manager.create(config)

        if not no_provision and config.get("PROVISIONING_PLAYBOOK"):
            _run_provisioning(infra_id, config, infra_type)

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

            # Clear provisioning status
            provision_manager = ProvisioningManager(infra_id)
            provision_manager.clear_provisioned_status()
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

            # Clear provisioning status
            provision_manager = ProvisioningManager(infra_id)
            provision_manager.clear_provisioned_status()
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
