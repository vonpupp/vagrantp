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

        Raises:
            VagrantpError: If configuration has errors.
        """
        try:
            provider = config.get("PROVIDER", "virtualbox")
            box = config.get("BOX", "generic/alpine319")
            memory = config.get("MEMORY", "2048")
            cpus = config.get("CPUS", "2")
            disk_size = config.get("DISK_SIZE", "20G")
            network_mode = config.get("NETWORK_MODE", "default")
            ip_address = config.get("IP_ADDRESS", "")
            ports_str = config.get("PORTS", "")

            # Parse port mappings
            ports = self._parse_ports(ports_str) if ports_str else []

            # Build network configuration
            network_config = self._build_network_config(network_mode, ip_address, ports)

            # Build Vagrantfile
            vagrantfile_content = f"""# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "{box}"

  config.vm.provider "{provider}" do |vb|
    vb.memory = {memory}
    vb.cpus = {cpus}
    vb.disk_size.size = "{disk_size}"
  end

{network_config}

  config.ssh.forward_agent = true
end
"""

            self.vagrantfile_path.write_text(vagrantfile_content)

        except Exception as e:
            raise VagrantpError(
                f"Failed to generate Vagrantfile: {e}", ErrorCode.GENERAL_ERROR
            )

    def _build_network_config(
        self, network_mode: str, ip_address: str, ports: list
    ) -> str:
        """Build network configuration section for Vagrantfile.

        Args:
            network_mode: Network mode (bridge or default).
            ip_address: Fixed IP address if specified.
            ports: List of port mappings.

        Returns:
            Network configuration string for Vagrantfile.
        """
        lines = []

        # Add network mode
        if network_mode == "bridge":
            lines.append('  config.vm.network "public_network"')
        elif ip_address:
            lines.append(f'  config.vm.network "public_network", ip: "{ip_address}"')
        else:
            lines.append('  config.vm.network "private_network", type: "dhcp"')

        # Add port forwarding
        for port in ports:
            if port["auto"]:
                lines.append(
                    f'  config.vm.network "forwarded_port", guest: {port["container"]}, host: 0, auto_correct: true'
                )
            else:
                lines.append(
                    f'  config.vm.network "forwarded_port", guest: {port["container"]}, host: {port["host"]}'
                )

        return "\n".join(lines)

    def _parse_ports(self, ports_str: str) -> list:
        """Parse port mappings string.

        Args:
            ports_str: Port mapping string (e.g., '8080:80,auto:443').

        Returns:
            List of port mapping dictionaries.
        """
        ports = []

        for mapping in ports_str.split(","):
            mapping = mapping.strip()

            if ":" not in mapping:
                continue

            host_port, container_port = mapping.split(":", 1)
            host_port = host_port.strip()
            container_port = container_port.strip()

            try:
                if host_port.lower() == "auto":
                    ports.append(
                        {"host": 0, "container": int(container_port), "auto": True}
                    )
                else:
                    ports.append(
                        {
                            "host": int(host_port),
                            "container": int(container_port),
                            "auto": False,
                        }
                    )
            except ValueError:
                continue

        return ports
