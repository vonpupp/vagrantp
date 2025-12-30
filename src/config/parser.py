"""Configuration file parser for .env files."""

import ipaddress
import os
import re
from pathlib import Path


class ValidationError(Exception):
    """Configuration validation error."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class ValidationResult:
    """Result of configuration validation."""

    def __init__(
        self,
        valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.valid = valid
        self.errors: list[str] = errors if errors is not None else []
        self.warnings: list[str] = warnings if warnings is not None else []


class ConfigurationParser:
    """Parser for .env configuration files."""

    def __init__(self, env_path: Path | None = None):
        """Initialize parser with optional .env file path.

        Args:
            env_path: Path to .env file. If None, looks in current directory.
        """
        self.env_path = env_path or Path.cwd() / ".env"
        self.config: dict[str, str] = {}

    def load(self) -> dict[str, str]:
        """Load and parse .env file from current directory.

        Returns:
            Dictionary of configuration key-value pairs.

        Raises:
            FileNotFoundError: If .env file doesn't exist.
        """
        if not self.env_path.exists():
            raise FileNotFoundError(f"Configuration file {self.env_path} not found")

        # Clear config to avoid contamination from previous loads
        self.config = {}

        # Read and parse .env file line by line
        with open(self.env_path) as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    self.config[key.strip()] = value.strip()

        # Also update environment variables for subprocess calls
        os.environ.update(self.config)

        return self.config

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get configuration value by key.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self.config.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found or invalid.

        Returns:
            Integer value.
        """
        try:
            return int(self.config.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Boolean value.
        """
        value = self.config.get(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        return default

    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string with unit suffix (e.g., '2G', '512M').

        Args:
            memory_str: Memory string with optional unit.

        Returns:
            Memory in MB.

        Raises:
            ValidationError: If format is invalid.
        """
        memory_str = memory_str.strip().upper()

        if memory_str.isdigit():
            return int(memory_str)

        match = re.match(r"^(\d+)(G|M|GB|MB)?$", memory_str)
        if not match:
            raise ValidationError(f"Invalid MEMORY format: {memory_str}", "MEMORY")

        value, unit = match.groups()
        value = int(value)

        if unit in ("G", "GB"):
            return value * 1024
        else:  # M or MB
            return value

    def _parse_disk_size(self, disk_str: str) -> int:
        """Parse disk size string with unit suffix (e.g., '20G', '50000M').

        Args:
            disk_str: Disk size string with optional unit.

        Returns:
            Disk size in GB.

        Raises:
            ValidationError: If format is invalid.
        """
        disk_str = disk_str.strip().upper()

        if disk_str.isdigit():
            return int(disk_str)

        match = re.match(r"^(\d+)(G|M|GB|MB)?$", disk_str)
        if not match:
            raise ValidationError(f"Invalid DISK_SIZE format: {disk_str}", "DISK_SIZE")

        value, unit = match.groups()
        value = int(value)

        if unit in ("M", "MB"):
            return value // 1024
        else:  # G or GB
            return value

    def _parse_ports(self, ports_str: str) -> list[dict[str, int | bool]]:
        """Parse port forwarding string (e.g., '8080:80,auto:443').

        Args:
            ports_str: Port mapping string.

        Returns:
            List of port mapping dictionaries.

        Raises:
            ValidationError: If format is invalid.
        """
        ports = []

        for mapping in ports_str.split(","):
            mapping = mapping.strip()

            if ":" not in mapping:
                raise ValidationError(f"Invalid port mapping: {mapping}", "PORTS")

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
                raise ValidationError(f"Invalid port mapping: {mapping}", "PORTS")

        return ports

    def _validate_ipv4(self, ip_str: str) -> bool:
        """Validate IPv4 address format.

        Args:
            ip_str: IP address string.

        Returns:
            True if valid, False otherwise.
        """
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except ipaddress.AddressValueError:
            return False

    def _check_port_conflicts(self, ports: list[dict[str, int]]) -> list[int]:
        """Check for port conflicts with running infrastructure.

        Args:
            ports: List of port mappings.

        Returns:
            List of conflicting port numbers.
        """
        conflicts: list[int] = []

        # Extract host ports (excluding auto-assigned)
        host_ports = [p["host"] for p in ports if not p["auto"] and p["host"] > 0]

        # TODO: Check against existing infrastructure instances
        # This would require a global state registry or checking Vagrant/Podman state
        # For now, we'll return empty list
        # conflicts.extend([port for port in host_ports if self._is_port_in_use(port)])

        return conflicts

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use.

        Args:
            port: Port number to check.

        Returns:
            True if port is in use, False otherwise.
        """
        # TODO: Implement actual port checking
        # This could use socket, subprocess to netstat/ss, or check infrastructure registry
        return False

    def validate(self) -> ValidationResult:
        """Validate configuration values per data-model.md rules.

        Returns:
            ValidationResult with errors and warnings.

        Raises:
            ValidationError: If configuration has critical errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if "INFRA_TYPE" not in self.config:
            errors.append("INFRA_TYPE is required")
        else:
            infra_type = self.config["INFRA_TYPE"]
            if infra_type not in ("vm", "container"):
                errors.append(f"INFRA_TYPE must be 'vm' or 'container', got: {infra_type}")

            # Validate provider for VM
            if infra_type == "vm" and "PROVIDER" not in self.config:
                errors.append("PROVIDER is required for VM infrastructure")

            # Container-specific validation
            if infra_type == "container":
                # Containers don't require DISK_SIZE
                if "DISK_SIZE" in self.config:
                    warnings.append("DISK_SIZE is not applicable for container infrastructure")

        # Validate MEMORY
        if "MEMORY" in self.config:
            try:
                memory_mb = self._parse_memory(self.config["MEMORY"])
                if memory_mb < 512:
                    errors.append(f"MEMORY must be at least 512MB, got: {memory_mb}MB")
            except ValidationError as e:
                errors.append(e.message)

        # Validate CPUS
        if "CPUS" in self.config:
            try:
                cpus = int(self.config["CPUS"])
                if cpus < 1:
                    errors.append(f"CPUS must be at least 1, got: {cpus}")
            except ValueError:
                errors.append(f"Invalid CPUS value: {self.config['CPUS']}")

        # Validate DISK_SIZE
        if "DISK_SIZE" in self.config:
            try:
                disk_gb = self._parse_disk_size(self.config["DISK_SIZE"])
                if disk_gb < 5:
                    errors.append(f"DISK_SIZE must be at least 5GB, got: {disk_gb}GB")
            except ValidationError as e:
                errors.append(e.message)

        # Validate NETWORK_MODE
        if "NETWORK_MODE" in self.config:
            network_mode = self.config["NETWORK_MODE"]
            if network_mode not in ("bridge", "default"):
                errors.append(f"NETWORK_MODE must be 'bridge' or 'default', got: {network_mode}")

        # Validate IP_ADDRESS
        if "IP_ADDRESS" in self.config:
            if not self._validate_ipv4(self.config["IP_ADDRESS"]):
                errors.append(f"Invalid IP_ADDRESS format: {self.config['IP_ADDRESS']}")

        # Validate PORTS
        if "PORTS" in self.config:
            try:
                self._parse_ports(self.config["PORTS"])
            except ValidationError as e:
                errors.append(e.message)

        # Validate PROVISIONING_PLAYBOOK
        if "PROVISIONING_PLAYBOOK" in self.config:
            playbook_path = Path(self.config["PROVISIONING_PLAYBOOK"])
            if not playbook_path.exists():
                errors.append(
                    f"PROVISIONING_PLAYBOOK not found: {self.config['PROVISIONING_PLAYBOOK']}"
                )
            if playbook_path.suffix not in [".yml", ".yaml"]:
                errors.append("PROVISIONING_PLAYBOOK must be a .yml or .yaml file")

        # Validate PROVISIONING_VARS
        if "PROVISIONING_VARS" in self.config:
            vars_path = Path(self.config["PROVISIONING_VARS"])
            if not vars_path.exists():
                errors.append(f"PROVISIONING_VARS not found: {self.config['PROVISIONING_VARS']}")

        # Validate PROVISIONING_AUTO_INSTALL_ANSIBLE
        if "PROVISIONING_AUTO_INSTALL_ANSIBLE" in self.config:
            value = self.config["PROVISIONING_AUTO_INSTALL_ANSIBLE"].lower()
            if value not in ["true", "false", "1", "0", "yes", "no"]:
                errors.append(
                    "PROVISIONING_AUTO_INSTALL_ANSIBLE must be true/false, 1/0, or yes/no"
                )

        return ValidationResult(len(errors) == 0, errors, warnings)


def load_config(env_path: Path | None = None) -> dict[str, str]:
    """Load configuration from .env file.

    Args:
        env_path: Path to .env file. If None, uses current directory.

    Returns:
        Configuration dictionary.
    """
    parser = ConfigurationParser(env_path)
    return parser.load()
