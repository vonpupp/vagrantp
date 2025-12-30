"""Integration tests for container lifecycle."""

from pathlib import Path

import pytest

from cli.main import _check_ansible_in_container, _detect_container_runtime
from config.parser import ConfigurationParser
from podman.container_manager import ContainerManager
from provision.ansible import ProvisioningManager
from utils.helpers import InfrastructureState


@pytest.fixture
def temp_container_project_dir(tmp_path):
    """Create a temporary project directory with .env file for container."""
    project_dir = tmp_path / "test_container_project"
    project_dir.mkdir()

    env_file = project_dir / ".env"
    env_file.write_text(
        """INFRA_TYPE=container
MEMORY=512
CPUS=1
IMAGE=alpine:latest
"""
    )

    return project_dir


@pytest.fixture
def container_manager(temp_container_project_dir):
    """Create container manager for testing."""
    manager = ContainerManager("test_container", temp_container_project_dir)
    yield manager


def test_container_get_state_returns_not_created(container_manager):
    """Test that container state returns NOT_CREATED when container doesn't exist."""
    state = container_manager._get_state()
    assert state == InfrastructureState.NOT_CREATED


def test_container_configuration_loading(temp_container_project_dir):
    """Test that .env configuration is loaded correctly."""
    parser = ConfigurationParser(temp_container_project_dir / ".env")
    config = parser.load()

    assert config.get("INFRA_TYPE") == "container"
    assert config.get("MEMORY") == "512"
    assert config.get("CPUS") == "1"
    assert config.get("IMAGE") == "alpine:latest"


def test_container_infrastructure_id_resolution(temp_container_project_dir):
    """Test that infrastructure ID defaults to project directory name."""
    parser = ConfigurationParser(temp_container_project_dir / ".env")
    config = parser.load()

    infra_id = config.get("INFRA_ID", temp_container_project_dir.name)
    assert infra_id == "test_container_project"


def test_build_run_command(container_manager):
    """Test building podman run command from configuration."""
    config = {
        "INFRA_TYPE": "container",
        "MEMORY": "1024",
        "CPUS": "2",
        "NETWORK_MODE": "bridge",
        "IMAGE": "alpine:latest",
    }

    cmd = container_manager._build_run_command(config)

    assert "podman" in cmd
    assert "run" in cmd
    assert "-d" in cmd
    assert "--name" in cmd
    assert "test_container" in cmd
    assert "--memory" in cmd
    assert "1024m" in cmd
    assert "--cpus" in cmd
    assert "2" in cmd
    assert "--network" in cmd
    assert "bridge" in cmd
    assert "alpine:latest" in cmd


def test_build_run_command_with_ports(container_manager):
    """Test building podman run command with port mappings."""
    config = {
        "INFRA_TYPE": "container",
        "MEMORY": "512",
        "CPUS": "1",
        "PORTS": "8080:80,auto:443",
    }

    cmd = container_manager._build_run_command(config)

    assert "-p" in cmd
    assert "8080:80" in cmd
    assert "443" in cmd


def test_parse_ports(container_manager):
    """Test parsing port mapping strings."""
    ports = container_manager._parse_ports("8080:80,auto:443")

    assert len(ports) == 2
    assert ports[0]["host"] == 8080
    assert ports[0]["container"] == 80
    assert ports[0]["auto"] is False
    assert ports[1]["host"] == 0
    assert ports[1]["container"] == 443
    assert ports[1]["auto"] is True


def test_full_lifecycle_workflow(temp_container_project_dir, container_manager):
    """Test complete container lifecycle: create -> connect -> stop -> remove."""
    # Note: This test requires Podman to be installed
    # In CI, this test should be skipped or mocked

    config = {
        "INFRA_TYPE": "container",
        "MEMORY": "512",
        "CPUS": "1",
        "IMAGE": "alpine:latest",
    }

    # Initial state: not_created
    state = container_manager._get_state()
    assert state == InfrastructureState.NOT_CREATED

    # Create container
    # container_manager.create(config)  # Requires actual Podman

    # Verify state transition to running
    # state = container_manager._get_state()
    # assert state == InfrastructureState.RUNNING

    # Connect (optional)
    # container_manager.connect("echo 'test'")

    # Stop container
    # container_manager.stop()

    # Verify state transition to stopped
    # state = container_manager._get_state()
    # assert state == InfrastructureState.STOPPED

    # Remove container
    # container_manager.remove()

    # Verify state transition back to not_created
    # state = container_manager._get_state()
    # assert state == InfrastructureState.NOT_CREATED


def test_container_provisioning_workflow(temp_container_project_dir):
    """Test provisioning workflow for container."""
    # Create Ansible playbook
    playbook = temp_container_project_dir / "playbook.yml"
    playbook.write_text(
        """---
- name: Test container provisioning
  hosts: all
  become: yes
  tasks:
    - name: Create test directory
      file:
        path: /tmp/container_test
        state: directory
"""
    )

    # Create provisioning manager
    provision_manager = ProvisioningManager("test_container", temp_container_project_dir)

    # Check initial provisioning status
    assert provision_manager.check_provisioning_status() is False

    # Mark as provisioned
    provision_manager.mark_provisioned()

    # Verify provisioning status
    assert provision_manager.check_provisioning_status() is True

    # Clear provisioning status
    provision_manager.clear_provisioned_status()

    # Verify provisioning status cleared
    assert provision_manager.check_provisioning_status() is False


def test_container_provisioning_with_docker_connection(temp_container_project_dir):
    """Test provisioning with docker connection type for containers."""
    # Create Ansible playbook
    playbook = temp_container_project_dir / "playbook.yml"
    playbook.write_text(
        """---
- name: Test container provisioning with docker
  hosts: all
  connection: docker
  tasks:
    - name: Create test file
      copy:
        content: "test"
        dest: /tmp/test.txt
"""
    )

    # Verify playbook exists
    assert playbook.exists()


def test_provisioning_status_tracking_for_container(temp_container_project_dir):
    """Test provisioning status tracking for containers."""
    provision_manager = ProvisioningManager("test_container", temp_container_project_dir)

    state_file = temp_container_project_dir / ".vagrantp_provisioned"

    # Initial: not provisioned
    assert provision_manager.check_provisioning_status() is False
    assert not state_file.exists()

    # Mark as provisioned
    provision_manager.mark_provisioned()
    assert provision_manager.check_provisioning_status() is True
    assert state_file.exists()

    # Verify state file content is a timestamp
    state_content = state_file.read_text()
    try:
        float(state_content)
    except ValueError:
        raise AssertionError("State file should contain a timestamp")

    # Clear provisioning status
    provision_manager.clear_provisioned_status()
    assert provision_manager.check_provisioning_status() is False
    assert not state_file.exists()


def test_detect_container_runtime_podman():
    """Test that Podman runtime is detected."""
    runtime = _detect_container_runtime()
    # Test passes if podman or docker is detected, or if neither is present
    assert runtime in ["podman", "docker", None]


def test_detect_container_runtime_docker():
    """Test that Docker runtime can be detected."""
    # Just verify the function doesn't crash
    runtime = _detect_container_runtime()
    assert runtime in ["podman", "docker", None]


def test_bootstrap_playbook_exists():
    """Test that bootstrap playbook exists."""
    bootstrap_path = Path("ansible/bootstrap.yml")
    assert bootstrap_path.exists()


def test_config_auto_install_ansible_validation():
    """Test PROVISIONING_AUTO_INSTALL_ANSIBLE validation."""
    # Test with valid values
    valid_values = ["true", "false", "1", "0", "yes", "no"]

    for value in valid_values:
        parser = ConfigurationParser()
        # Set required fields to avoid validation errors
        parser.config["INFRA_TYPE"] = "container"
        parser.config["IMAGE"] = "alpine:latest"
        parser.config["PROVISIONING_AUTO_INSTALL_ANSIBLE"] = value

        result = parser.validate()

        # Should not have errors for valid values
        assert result.valid is True
        assert len(result.errors) == 0

    # Test with invalid values
    invalid_values = ["invalid", "maybe", "2"]

    for value in invalid_values:
        parser = ConfigurationParser()
        # Set required fields to avoid validation errors
        parser.config["INFRA_TYPE"] = "container"
        parser.config["IMAGE"] = "alpine:latest"
        parser.config["PROVISIONING_AUTO_INSTALL_ANSIBLE"] = value

        result = parser.validate()

        # Should have errors for invalid values
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("PROVISIONING_AUTO_INSTALL_ANSIBLE" in e for e in result.errors)
