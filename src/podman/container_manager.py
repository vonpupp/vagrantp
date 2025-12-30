"""Container manager for Podman-based infrastructure."""

import subprocess
from pathlib import Path
from typing import Any

from utils.helpers import (
    ErrorCode,
    InfrastructureState,
    ProviderNotAvailableError,
    VagrantpError,
    run_command,
)


class ContainerManager:
    """Manager for Podman-based containers."""

    def __init__(self, infra_id: str, project_dir: Path | None = None):
        """Initialize container manager.

        Args:
            infra_id: Infrastructure identifier.
            project_dir: Project directory. If None, uses current directory.
        """
        self.infra_id = infra_id
        self.project_dir = project_dir or Path.cwd()

    def _get_state(self) -> InfrastructureState:
        """Get current state of container by querying Podman directly.

        Returns:
            Current container state.
        """
        try:
            result = run_command(
                [
                    "podman",
                    "ps",
                    "-a",
                    "--format",
                    "{{.Names}}\t{{.Status}}",
                ],
                cwd=self.project_dir,
                check=False,
            )

            if result.returncode != 0:
                return InfrastructureState.NOT_CREATED

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) != 2:
                    continue

                name, status = parts
                if name == self.infra_id:
                    status_lower = status.lower()
                    if status_lower.startswith("up"):
                        return InfrastructureState.RUNNING
                    elif any(s in status_lower for s in ["stopped", "exited", "created"]):
                        return InfrastructureState.STOPPED
        except (subprocess.CalledProcessError, Exception):
            pass

        return InfrastructureState.NOT_CREATED

    def _get_ssh_host(self) -> str:
        """Get SSH host (IP address) of container.

        Returns:
            SSH host IP address.

        Raises:
            VagrantpError: If container is not running or IP cannot be determined.
        """
        state = self._get_state()
        if state != InfrastructureState.RUNNING:
            raise VagrantpError(
                f"Container '{self.infra_id}' is not running (state: {state.value})",
                ErrorCode.GENERAL_ERROR,
            )

        try:
            result = run_command(
                ["podman", "inspect", self.infra_id, "--format", "{{.NetworkSettings.IPAddress}}"],
                cwd=self.project_dir,
                check=True,
            )

            ip_address = result.stdout.strip() if result.stdout else ""
            if not ip_address:
                raise VagrantpError("Could not determine container IP address")

            return ip_address

        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to get container IP: {e}")

    def create(self, config: dict[str, Any]) -> None:
        """Create container from configuration.

        Args:
            config: Configuration dictionary.

        Raises:
            VagrantpError: If creation fails.
            ProviderNotAvailableError: If Podman is not available.
        """
        # Check if Podman is installed
        try:
            run_command(["podman", "--version"])
        except subprocess.CalledProcessError:
            raise ProviderNotAvailableError("podman")

        # Check if container already exists
        existing = self._check_container_exists()
        if existing:
            raise VagrantpError(
                f"Container '{self.infra_id}' already exists", ErrorCode.INFRA_EXISTS
            )

        print("  Creating container...")

        try:
            # Build podman run command
            cmd = self._build_run_command(config)

            # Run container in detached mode
            run_command(cmd, cwd=self.project_dir, capture_output=False)

            print("✓ Container created and running")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to create container: {e}")

    def start(self) -> None:
        """Start a stopped container.

        Raises:
            VagrantpError: If start fails.
        """
        state = self._get_state()

        if state == InfrastructureState.RUNNING:
            print(f"ℹ Container '{self.infra_id}' is already running")
            return

        if state == InfrastructureState.NOT_CREATED:
            print(f"ℹ Container '{self.infra_id}' does not exist")
            return

        print(f"  Starting container '{self.infra_id}'...")

        try:
            run_command(["podman", "start", self.infra_id], cwd=self.project_dir)
            print("✓ Container started")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to start container: {e}")

    def connect(self, command: str | None = None) -> None:
        """Establish SSH connection to container.

        Args:
            command: Optional command to execute.

        Raises:
            VagrantpError: If connection fails.
        """
        print("  Establishing SSH connection...")

        # Check state
        state = self._get_state()
        if state != InfrastructureState.RUNNING:
            raise VagrantpError(
                f"Container '{self.infra_id}' is not running (state: {state.value})",
                ErrorCode.GENERAL_ERROR,
            )

        try:
            # Use podman exec to connect
            if command:
                run_command(
                    ["podman", "exec", "-it", self.infra_id, "/bin/sh", "-c", command],
                    cwd=self.project_dir,
                    capture_output=False,
                )
            else:
                run_command(
                    ["podman", "exec", "-it", self.infra_id, "/bin/sh"],
                    cwd=self.project_dir,
                    capture_output=False,
                )

            print("✓ Connected")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to connect to container: {e}")

    def stop(self, force: bool = False) -> None:
        """Stop container.

        Args:
            force: Force stop without graceful shutdown.

        Raises:
            VagrantpError: If stop fails.
        """
        state = self._get_state()

        if state == InfrastructureState.NOT_CREATED:
            print(f"ℹ Container '{self.infra_id}' does not exist")
            return

        if state != InfrastructureState.RUNNING:
            print(f"ℹ Container '{self.infra_id}' is not running (state: {state.value})")
            return

        print(f"  Stopping container '{self.infra_id}'...")

        try:
            if force:
                run_command(["podman", "kill", self.infra_id], cwd=self.project_dir)
            else:
                run_command(["podman", "stop", self.infra_id], cwd=self.project_dir)

            print("✓ Container stopped")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to stop container: {e}")

    def remove(self, force: bool = False) -> None:
        """Remove container and all resources.

        Args:
            force: Force removal without stopping first.

        Raises:
            VagrantpError: If removal fails.
        """
        state = self._get_state()

        if state == InfrastructureState.NOT_CREATED:
            print(f"ℹ Container '{self.infra_id}' does not exist")
            return

        if state == InfrastructureState.RUNNING:
            if not force:
                print(f"  Stopping container '{self.infra_id}' first...")
                self.stop(force=False)
            else:
                print(f"  Force stopping container '{self.infra_id}'...")
                self.stop(force=True)

        print(f"  Removing container '{self.infra_id}'...")

        try:
            # Remove container
            run_command(["podman", "rm", self.infra_id], cwd=self.project_dir)

            # Remove associated volumes (optional)
            # run_command(['podman', 'volume', 'rm', f'{self.infra_id}-data'], check=False)

            print("✓ Container removed")
        except subprocess.CalledProcessError as e:
            raise VagrantpError(f"Failed to remove container: {e}")

    def _check_container_exists(self) -> bool:
        """Check if container already exists.

        Returns:
            True if container exists, False otherwise.
        """
        try:
            result = run_command(
                [
                    "podman",
                    "ps",
                    "-a",
                    "--format",
                    "{{.Names}}",
                ],
                cwd=self.project_dir,
                check=False,
            )
            return self.infra_id in result.stdout.strip().split("\n")
        except subprocess.CalledProcessError:
            return False

    def _build_run_command(self, config: dict[str, Any]) -> list:
        """Build podman run command from configuration.

        Args:
            config: Configuration dictionary.

        Returns:
            List of command arguments.
        """
        cmd = ["podman", "run", "-d", "--name", self.infra_id]

        # Add resource limits (MEMORY, CPUS)
        memory = config.get("MEMORY", "512")
        cpus = config.get("CPUS", "1")

        cmd.extend(["--memory", f"{memory}m"])
        cmd.extend(["--cpus", str(cpus)])

        # Add networking configuration (NETWORK_MODE, IP_ADDRESS)
        network_mode = config.get("NETWORK_MODE", "default")
        if network_mode == "bridge":
            cmd.extend(["--network", "bridge"])
        elif network_mode == "default":
            cmd.extend(["--network", "default"])

        # Add IP address (if specified)
        ip_address = config.get("IP_ADDRESS")
        if ip_address:
            cmd.extend(["--ip", str(ip_address)])

        # Add port mappings (PORTS)
        ports_str = config.get("PORTS", "")
        if ports_str:
            for port_mapping in self._parse_ports(ports_str):
                if port_mapping["auto"]:
                    cmd.extend(["-p", f"{port_mapping['container']}"])
                else:
                    cmd.extend(["-p", f"{port_mapping['host']}:{port_mapping['container']}"])

        # Add image (default to alpine)
        image = config.get("IMAGE", "alpine:latest")
        if image:
            cmd.append(str(image))

        # Add default command to keep container running
        cmd.extend(["/bin/sh", "-c", "tail -f /dev/null"])

        return cmd

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
                    ports.append({"host": 0, "container": int(container_port), "auto": True})
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
