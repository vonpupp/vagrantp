"""Ansible provisioning orchestrator."""

import subprocess
from pathlib import Path
from typing import Any

from utils.helpers import (
    ErrorCode,
    ProvisioningFailedError,
    VagrantpError,
    run_command,
)


class AnsibleProvisioner:
    """Orchestrator for Ansible-based provisioning."""

    def __init__(
        self, project_dir: Path | None = None, infra_type: str = "vm", infra_id: str | None = None
    ):
        """Initialize Ansible provisioner.

        Args:
            project_dir: Project directory. If None, uses current directory.
            infra_type: Infrastructure type ('vm' or 'container').
            infra_id: Infrastructure identifier (for containers, used with podman commands).
        """
        self.project_dir = project_dir or Path.cwd()
        self.provisioning_marker = self.project_dir / ".provisioned"
        self.infra_type = infra_type
        self.infra_id = infra_id

    def execute(
        self,
        playbook_path: Path,
        inventory_path: str,
        vars_path: Path | None = None,
        dry_run: bool = False,
        extra_vars: dict[str, Any] | None = None,
    ) -> None:
        """Execute Ansible playbook.

        Args:
            playbook_path: Path to Ansible playbook.
            inventory_path: Inventory string (e.g., IP address or hostname).
            vars_path: Optional path to Ansible variables file.
            dry_run: Run in dry-run mode (--check).
            extra_vars: Extra variables to pass to Ansible.

        Raises:
            VagrantpError: If playbook execution fails.
            ProvisioningFailedError: If Ansible playbook fails.
        """
        print("  Running Ansible provisioning...")

        # Check if playbook exists
        if not playbook_path.exists():
            raise ProvisioningFailedError(f"Playbook not found: {playbook_path}")

        # Check if vars file exists (if specified)
        if vars_path and not vars_path.exists():
            raise ProvisioningFailedError(f"Variables file not found: {vars_path}")

        # Create temporary inventory file
        inventory_file = self._create_inventory_file(inventory_path)

        # For containers, ensure SSH is installed first
        if self.infra_type == "container":
            self._ensure_ssh_in_container(inventory_path)

        # Verify SSH connection before running playbook
        self._verify_ssh_connection(inventory_path)

        # Build ansible-playbook command
        cmd = ["ansible-playbook", str(playbook_path), "-i", str(inventory_file)]

        # Add variables file if specified
        if vars_path:
            cmd.extend(["-e", f"@{vars_path}"])

        # Add extra vars if specified
        if extra_vars:
            for key, value in extra_vars.items():
                cmd.extend(["-e", f"{key}={value}"])

        # Add dry-run flag if specified
        if dry_run:
            cmd.append("--check")
            print("  [DRY-RUN] Validating playbook without making changes...")

        try:
            # Run ansible-playbook and capture output
            result = run_command(
                cmd,
                cwd=self.project_dir,
                capture_output=False,
                check=False,
            )

            if result.returncode != 0:
                raise ProvisioningFailedError(
                    f"Playbook execution failed with exit code {result.returncode}"
                )

            # Mark as provisioned if not dry-run
            if not dry_run:
                self._mark_provisioned()

            # Clean up temporary inventory file
            if inventory_file.exists():
                inventory_file.unlink()

            print("✓ Provisioning completed")

        except subprocess.CalledProcessError as e:
            # Clean up temporary inventory file on error
            if inventory_file.exists():
                inventory_file.unlink()
            raise ProvisioningFailedError(f"Playbook execution failed: {e}")

    def _create_inventory_file(self, inventory_path: str) -> Path:
        """Create a temporary Ansible inventory file.

        Args:
            inventory_path: Inventory target (IP address or hostname).

        Returns:
            Path to the created inventory file.
        """
        inventory_file = self.project_dir / ".ansible_inventory"

        if self.infra_type == "container":
            # Use podman connection for containers (no SSH needed)
            # ansible_host should be container ID/name, not IP
            container_host = self.infra_id if self.infra_id else inventory_path
            # Set remote_tmp to /tmp to avoid home directory issues in containers
            inventory_content = (
                f"[default]\n"
                f"{inventory_path} ansible_connection=podman ansible_host={container_host} ansible_remote_tmp=/tmp/ansible-tmp\n"
            )
        else:
            # Use SSH connection for VMs
            inventory_content = (
                f"[default]\n{inventory_path} ansible_connection=ssh ansible_user=root\n"
            )

        inventory_file.write_text(inventory_content)
        return inventory_file

    def _ensure_ssh_in_container(self, inventory_path: str) -> None:
        """Ensure SSH is installed in container.

        Args:
            inventory_path: Container name or IP.
        """
        print("  Ensuring SSH is available in container...")

        try:
            # Install openssh and python in container using container name/ID, not IP
            container_target = self.infra_id if self.infra_id else inventory_path
            result = run_command(
                [
                    "podman",
                    "exec",
                    container_target,
                    "pacman",
                    "-Sy",
                    "--noconfirm",
                    "openssh",
                    "python",
                ],
                cwd=self.project_dir,
                check=False,
            )

            if result.returncode != 0:
                print("  ℹ SSH installation failed (continuing anyway)")
            else:
                print("  ✓ SSH installed")

        except Exception:
            print("  ℹ SSH installation skipped (continuing)")

    def _verify_ssh_connection(self, inventory_path: str) -> None:
        """Verify SSH connection to target host.

        Args:
            inventory_path: Inventory target (IP address or hostname).

        Raises:
            VagrantpError: If SSH connection fails.
        """
        print("  Verifying connection...")

        try:
            if self.infra_type == "container":
                # For containers, verify podman container is running using container ID, not IP
                container_target = self.infra_id if self.infra_id else inventory_path
                result = run_command(
                    ["podman", "inspect", "--format={{.State.Status}}", container_target],
                    cwd=self.project_dir,
                    check=False,
                )

                if result.returncode != 0 or "running" not in result.stdout.lower():
                    raise VagrantpError(
                        f"Container {container_target} is not running",
                        ErrorCode.PROVISIONING_FAILED,
                        suggestion="Check that container is running with 'podman ps'",
                    )
            else:
                # For VMs, try to ping host using ansible with inline inventory
                result = run_command(
                    ["ansible", "all", "-i", f"{inventory_path},", "-m", "ping", "--timeout", "10"],
                    cwd=self.project_dir,
                    check=False,
                )

                if result.returncode != 0:
                    raise VagrantpError(
                        f"SSH connection verification failed for {inventory_path}",
                        ErrorCode.PROVISIONING_FAILED,
                        suggestion="Check that infrastructure is running and SSH is accessible",
                    )

            print("  ✓ Connection verified")

        except Exception as e:
            raise VagrantpError(
                f"Failed to verify connection: {e}",
                ErrorCode.PROVISIONING_FAILED,
                suggestion="Check that infrastructure is running and accessible",
            )

    def _mark_provisioned(self) -> None:
        """Mark infrastructure as provisioned."""
        self.provisioning_marker.write_text(str(Path.cwd()))

    def is_provisioned(self) -> bool:
        """Check if infrastructure has been provisioned.

        Returns:
            True if provisioning marker exists, False otherwise.
        """
        return self.provisioning_marker.exists()

    def clear_provisioning_marker(self) -> None:
        """Clear provisioning marker."""
        if self.provisioning_marker.exists():
            self.provisioning_marker.unlink()
