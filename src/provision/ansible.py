"""Ansible provisioning orchestrator."""

import subprocess
import time
from pathlib import Path

from utils.helpers import (
    ErrorCode,
    ProvisioningFailedError,
    VagrantpError,
    run_command,
)


class ProvisioningManager:
    """Orchestrator for Ansible provisioning."""

    def __init__(self, infra_id: str, project_dir: Path | None = None):
        """Initialize provisioning manager.

        Args:
            infra_id: Infrastructure identifier.
            project_dir: Project directory. If None, uses current directory.
        """
        self.infra_id = infra_id
        self.project_dir = project_dir or Path.cwd()

    def execute(
        self,
        playbook_path: str,
        inventory: str | None = None,
        extra_vars: str | None = None,
        dry_run: bool = False,
        ssh_user: str | None = None,
        ssh_key: str | None = None,
        use_connection: str = "ssh",
    ) -> None:
        """Execute Ansible playbook against infrastructure.

        Args:
            playbook_path: Path to Ansible playbook.
            inventory: Inventory string (e.g., "host1,host2").
            extra_vars: Extra variables for playbook.
            dry_run: Run in dry-run mode (check mode).
            ssh_user: SSH username for connection.
            ssh_key: SSH key path for connection.
            use_connection: Connection type (ssh, local, docker, podman).

        Raises:
            ProvisioningFailedError: If provisioning fails.
            VagrantpError: If SSH connection fails.
        """
        print("  → Running Ansible provisioning...")

        if not playbook_path:
            raise ProvisioningFailedError("Playbook path is required")

        # Verify playbook exists
        playbook = Path(playbook_path)
        if not playbook.exists():
            raise ProvisioningFailedError(f"Playbook not found: {playbook_path}")

        # Check if Ansible is installed
        try:
            run_command(["ansible", "--version"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ProvisioningFailedError("Ansible is not installed")

        # Build ansible-playbook command
        cmd = ["ansible-playbook", str(playbook)]

        # Add dry-run mode
        if dry_run:
            cmd.append("--check")

        # Add inventory
        if inventory:
            cmd.extend(["-i", inventory])

        # Add extra vars
        if extra_vars:
            cmd.extend(["--extra-vars", extra_vars])

        # Add SSH options if specified
        if ssh_user:
            cmd.extend(["-u", ssh_user])
        if ssh_key:
            cmd.extend(["--private-key", ssh_key])

        # Add connection type for containers
        if use_connection != "ssh":
            cmd.extend(["-e", f"ansible_connection={use_connection}"])

        try:
            # Execute playbook with real-time output
            start_time = time.time()

            # Stream output in real-time
            process = subprocess.Popen(
                cmd,
                cwd=self.project_dir,
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
                raise ProvisioningFailedError(
                    f"Playbook execution failed with exit code {returncode}"
                )

            print(f"✓ Provisioning completed ({duration:.1f}s)")

        except subprocess.CalledProcessError as e:
            raise ProvisioningFailedError(f"Playbook execution failed: {e}")

    def verify_ssh_connection(
        self, host: str, ssh_user: str | None = None, ssh_key: str | None = None
    ) -> bool:
        """Verify SSH connection to infrastructure before provisioning.

        Args:
            host: Host address (IP or hostname).
            ssh_user: SSH username.
            ssh_key: SSH key path.

        Returns:
            True if connection successful, False otherwise.

        Raises:
            VagrantpError: If connection fails.
        """
        print("  → Verifying SSH connection...")

        cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]

        if ssh_user:
            cmd.append(f"{ssh_user}@{host}")
        else:
            cmd.append(host)

        if ssh_key:
            cmd.extend(["-i", ssh_key])

        cmd.extend(["echo", "connection_ok"])

        try:
            result = run_command(cmd, cwd=self.project_dir, check=False)
            if "connection_ok" in result.stdout:
                print("  ✓ SSH connection verified")
                return True
            else:
                raise VagrantpError(
                    f"SSH connection failed to {host}",
                    ErrorCode.GENERAL_ERROR,
                    suggestion="Check network connectivity and SSH configuration",
                )
        except subprocess.CalledProcessError as e:
            raise VagrantpError(
                f"SSH connection failed to {host}: {e}",
                ErrorCode.GENERAL_ERROR,
                suggestion="Check network connectivity and SSH configuration",
            )

    def check_provisioning_status(self) -> bool:
        """Check if provisioning has already succeeded.

        Returns:
            True if provisioning succeeded, False otherwise.
        """
        # Check for provisioning state file
        state_file = self.project_dir / ".vagrantp_provisioned"

        if state_file.exists():
            return True

        return False

    def mark_provisioned(self) -> None:
        """Mark infrastructure as provisioned."""
        state_file = self.project_dir / ".vagrantp_provisioned"
        state_file.write_text(str(time.time()))

    def clear_provisioned_status(self) -> None:
        """Clear provisioning status."""
        state_file = self.project_dir / ".vagrantp_provisioned"
        if state_file.exists():
            state_file.unlink()
