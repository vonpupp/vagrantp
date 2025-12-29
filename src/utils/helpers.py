"""Utility functions and helper classes."""

import os
import subprocess
import sys
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class InfrastructureState(Enum):
    """Infrastructure state enumeration."""

    NOT_CREATED = "not_created"
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    REMOVING = "removing"


class StateManager:
    """Manager for tracking infrastructure states."""

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize state manager.

        Args:
            state_file: Path to state file. If None, uses current directory.
        """
        self.state_file = state_file or Path.cwd() / ".vagrantp-state"

    def get_state(self, infra_id: str) -> InfrastructureState:
        """Get current state of infrastructure.

        Args:
            infra_id: Infrastructure identifier.

        Returns:
            Current infrastructure state.
        """
        if not self.state_file.exists():
            return InfrastructureState.NOT_CREATED

        states = self._load_states()
        state_str = states.get(infra_id, InfrastructureState.NOT_CREATED.value)

        try:
            return InfrastructureState(state_str)
        except ValueError:
            return InfrastructureState.NOT_CREATED

    def set_state(self, infra_id: str, state: InfrastructureState) -> None:
        """Set infrastructure state.

        Args:
            infra_id: Infrastructure identifier.
            state: New state.
        """
        states = self._load_states()
        states[infra_id] = state.value
        self._save_states(states)

    def _load_states(self) -> Dict[str, str]:
        """Load states from file.

        Returns:
            Dictionary of infrastructure IDs to states.
        """
        states = {}
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                for line in f:
                    if "=" in line:
                        infra_id, state = line.strip().split("=", 1)
                        states[infra_id] = state
        return states

    def _save_states(self, states: Dict[str, str]) -> None:
        """Save states to file.

        Args:
            states: Dictionary of infrastructure IDs to states.
        """
        with open(self.state_file, "w") as f:
            for infra_id, state in states.items():
                f.write(f"{infra_id}={state}\n")


class ErrorCode(Enum):
    """Error codes matching contracts/cli-api.md."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIG_ERROR = 2
    INFRA_EXISTS = 3
    INSUFFICIENT_RESOURCES = 4
    PROVIDER_NOT_AVAILABLE = 5
    PORT_CONFLICT = 6
    PROVISIONING_FAILED = 7


class VagrantpError(Exception):
    """Base exception for Vagrantp errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.GENERAL_ERROR,
        suggestion: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.suggestion = suggestion
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary.

        Returns:
            Error dictionary with code, message, and suggestion.
        """
        result = {"code": self.code.name, "message": self.message}
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


class ConfigNotFoundError(VagrantpError):
    """Configuration file not found."""

    def __init__(self, env_path: Optional[Path] = None):
        message = (
            f"Configuration file {env_path or '.env'} not found in current directory"
        )
        super().__init__(
            message,
            ErrorCode.CONFIG_ERROR,
            suggestion="Create a .env file with required INFRA_TYPE field",
        )


class ConfigInvalidError(VagrantpError):
    """Invalid configuration."""

    def __init__(self, details: str, field: Optional[str] = None):
        message = f"Invalid configuration: {details}"
        super().__init__(
            message,
            ErrorCode.CONFIG_ERROR,
            suggestion=f"Check {field} field in .env file" if field else None,
        )


class InfrastructureExistsError(VagrantpError):
    """Infrastructure already exists."""

    def __init__(self, infra_id: str, state: str):
        message = f"Infrastructure '{infra_id}' already exists (state: {state})"
        super().__init__(
            message,
            ErrorCode.INFRA_EXISTS,
            suggestion="Run 'vagrantp ssh' to connect, or 'vagrantp stop' then 'vagrantp rm' to recreate",
        )


class InsufficientResourcesError(VagrantpError):
    """Insufficient host resources."""

    def __init__(self, resource: str, needed: str, available: str):
        message = f"Insufficient {resource}: need {needed}, {available} available"
        super().__init__(
            message,
            ErrorCode.INSUFFICIENT_RESOURCES,
            suggestion="Stop other running projects, or reduce resource requirements in .env",
        )


class ProviderNotAvailableError(VagrantpError):
    """Provider not available."""

    def __init__(self, provider: str):
        message = f"Provider '{provider}' is not installed or not configured"
        super().__init__(
            message,
            ErrorCode.PROVIDER_NOT_AVAILABLE,
            suggestion=f"Install {provider} and verify it's configured",
        )


class PortConflictError(VagrantpError):
    """Port conflict."""

    def __init__(self, port: int, existing_project: Optional[str] = None):
        message = f"Port {port} is already in use"
        if existing_project:
            message += f" by project '{existing_project}'"
        super().__init__(
            message,
            ErrorCode.PORT_CONFLICT,
            suggestion="Use a different port in .env file, or stop the conflicting project",
        )


class ProvisioningFailedError(VagrantpError):
    """Provisioning failed."""

    def __init__(self, details: str):
        message = f"Ansible playbook failed: {details}"
        super().__init__(
            message,
            ErrorCode.PROVISIONING_FAILED,
            suggestion="Check playbook syntax and execution logs",
        )


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run shell command with subprocess.

    Args:
        cmd: Command and arguments as list.
        cwd: Working directory for command.
        capture_output: Whether to capture stdout/stderr.
        check: Whether to raise exception on non-zero exit.

    Returns:
        Completed process result.

    Raises:
        subprocess.CalledProcessError: If command fails and check=True.
    """
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=True, check=check
        )
    except subprocess.CalledProcessError as e:
        if capture_output:
            error_msg = f"Command failed: {' '.join(cmd)}\n"
            if e.stderr:
                error_msg += f"Error output: {e.stderr}"
            raise subprocess.CalledProcessError(
                e.returncode, cmd, e.stdout, error_msg
            ) from e
        raise


def ensure_dir(path: Path) -> None:
    """Ensure directory exists, create if necessary.

    Args:
        path: Directory path.
    """
    path.mkdir(parents=True, exist_ok=True)


def read_file(path: Path) -> str:
    """Read file contents.

    Args:
        path: File path.

    Returns:
        File contents.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    return path.read_text()


def write_file(path: Path, content: str) -> None:
    """Write content to file.

    Args:
        path: File path.
        content: Content to write.
    """
    ensure_dir(path.parent)
    path.write_text(content)


class TemplateRenderer:
    """Base class for ERB template rendering."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template renderer.

        Args:
            template_dir: Directory containing templates. If None, uses templates/.
        """
        self.template_dir = template_dir or Path("templates")

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render ERB template with context.

        Args:
            template_name: Template file name.
            context: Dictionary of template variables.

        Returns:
            Rendered template content.

        Raises:
            FileNotFoundError: If template doesn't exist.
        """
        template_path = self.template_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        template = read_file(template_path)

        for key, value in context.items():
            placeholder = f"<%= {key} %>"
            template = template.replace(placeholder, str(value))

        return template


def get_logger(name: str):
    """Get logger instance.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    import logging

    return logging.getLogger(name)
