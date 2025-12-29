"""VM manager for Vagrant-based infrastructure."""

import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any
from utils.helpers import (
    run_command,
    ProviderNotAvailableError,
    VagrantpError,
    InfrastructureState,
    StateManager,
    ErrorCode,
)


class VMManager:
    """Manager for Vagrant-based virtual machines."""

    def __init__(self, infra_id: str, project_dir: Optional[Path] = None):
        """Initialize VM manager.

        Args:
            infra_id: Infrastructure identifier.
            project_dir: Project directory. If None, uses current directory.
        """
        self.infra_id = infra_id
        self.project_dir = project_dir or Path.cwd()
        self.vagrantfile_path = self.project_dir / "Vagrantfile"
        self.state_manager = StateManager(self.project_dir / ".vagrantp-state")

    def create(self, config: Dict[str, Any]) -> None:
        """Create VM from configuration.

        Args:
            config: Configuration dictionary.

        Raises:
            VagrantpError: If creation fails.
            ProviderNotAvailableError: If provider is not available.
        """
        print("  Generating Vagrantfile...")

        # Generate Vagrantfile from template
        self._generate_vagrantfile(config)

        # Check if Vagrant is installed
        try:
            run_command(["vagrant", "--version"])
        except subprocess.CalledProcessError:
            provider = config.get("PROVIDER", "virtualbox")
            raise ProviderNotAvailableError(provider)

        # Update state to creating
        self.state_manager.set_state(self.infra_id, InfrastructureState.CREATING)

        print("  Creating VM...")

        try:
            # Run vagrant up
            run_command(["vagrant", "up"], cwd=self.project_dir, check=False)

            # Update state to running
            self.state_manager.set_state(self.infra_id, InfrastructureState.RUNNING)

            print("✓ VM created and running")
        except subprocess.CalledProcessError as e:
            self.state_manager.set_state(self.infra_id, InfrastructureState.NOT_CREATED)
            raise VagrantpError(f"Failed to create VM: {e}")

    def connect(self, command: Optional[str] = None) -> None:
        """Establish SSH connection to VM.

        Args:
            command: Optional command to execute.

        Raises:
            VagrantpError: If connection fails.
        """
        print("  Establishing SSH connection...")

        # Check state
        state = self.state_manager.get_state(self.infra_id)
        if state != InfrastructureState.RUNNING:
            raise VagrantpError(
                f"VM '{self.infra_id}' is not running (state: {state.value})",
                ErrorCode.GENERAL_ERROR,
            )

        try:
            if command:
                run_command(
                    ["vagrant", "ssh", "-c", command],
                    cwd=self.project_dir,
                    capture_output=False,
                )
            else:
                run_command(
                    ["vagrant", "ssh"], cwd=self.project_dir, capture_output=False
                )

            print("✓ Connected")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to connect to VM: {e}")

    def stop(self, force: bool = False) -> None:
        """Stop VM.

        Args:
            force: Force stop without graceful shutdown.

        Raises:
            VagrantpError: If stop fails.
        """
        state = self.state_manager.get_state(self.infra_id)

        if state == InfrastructureState.NOT_CREATED:
            print(f"ℹ VM '{self.infra_id}' does not exist")
            return

        if state != InfrastructureState.RUNNING:
            print(f"ℹ VM '{self.infra_id}' is not running (state: {state.value})")
            return

        print(f"  Stopping VM '{self.infra_id}'...")

        try:
            if force:
                run_command(["vagrant", "halt", "--force"], cwd=self.project_dir)
            else:
                run_command(["vagrant", "halt"], cwd=self.project_dir)

            self.state_manager.set_state(self.infra_id, InfrastructureState.STOPPED)
            print("✓ VM stopped")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to stop VM: {e}")

    def remove(self, force: bool = False) -> None:
        """Remove VM and all resources.

        Args:
            force: Force removal without stopping first.

        Raises:
            VagrantpError: If removal fails.
        """
        state = self.state_manager.get_state(self.infra_id)

        if state == InfrastructureState.NOT_CREATED:
            print(f"ℹ VM '{self.infra_id}' does not exist")
            return

        if state == InfrastructureState.RUNNING:
            if not force:
                print(f"  Stopping VM '{self.infra_id}' first...")
                self.stop(force=False)
            else:
                print(f"  Force stopping VM '{self.infra_id}'...")
                self.stop(force=True)

        print(f"  Removing VM '{self.infra_id}'...")

        self.state_manager.set_state(self.infra_id, InfrastructureState.REMOVING)

        try:
            run_command(["vagrant", "destroy", "--force"], cwd=self.project_dir)

            self.state_manager.set_state(self.infra_id, InfrastructureState.NOT_CREATED)
            print("✓ VM removed")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to remove VM: {e}")

    def _generate_vagrantfile(self, config: Dict[str, Any]) -> None:
        """Generate Vagrantfile from configuration.

        Args:
            config: Configuration dictionary.
        """
        provider = config.get("PROVIDER", "virtualbox")

        vagrantfile_content = f"""# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "generic/alpine319"

  config.vm.provider "{provider}" do |vb|
    vb.memory = {config.get("MEMORY", "2048")}
    vb.cpus = {config.get("CPUS", "2")}
  end

  config.ssh.forward_agent = true
end
"""

        self.vagrantfile_path.write_text(vagrantfile_content)
