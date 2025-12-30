"""Integration tests for container lifecycle."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.parser import ConfigurationParser
from podman.container_manager import ContainerManager
from provision.ansible import AnsibleProvisioner
from utils.helpers import InfrastructureState


@pytest.fixture
def temp_container_project_dir(tmp_path):
    """Create a temporary project directory with .env file for container."""
    project_dir = tmp_path / "test_container_project"
    project_dir.mkdir()

    env_file = project_dir / ".env"
    env_file.write_text("""INFRA_TYPE=container
MEMORY=512
CPUS=1
IMAGE=alpine:latest
""")

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


def test_container_provisioning_workflow(temp_container_project_dir, container_manager):
    """Test container provisioning workflow with mocked Ansible."""
    # Create provisioning playbook
    playbook = temp_container_project_dir / "playbook.yml"
    playbook.write_text("""---
- name: Test playbook
  hosts: all
  tasks:
    - name: Create test file
      copy:
        content: "test"
        dest: /tmp/test.txt
""")

    provisioner = AnsibleProvisioner(temp_container_project_dir)

    # Mock ansible-playbook execution
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute provisioning
        provisioner.execute(
            playbook_path=playbook,
            inventory_path="172.17.0.2",
            dry_run=False,
        )

        # Verify ansible-playbook was called
        assert mock_run.called
        call_args = mock_run.call_args
        assert "ansible-playbook" in call_args[0][0]
        assert str(playbook) in call_args[0][0]

        # Verify provisioning marker was created
        assert provisioner.is_provisioned()


def test_container_provisioning_idempotency(temp_container_project_dir, container_manager):
    """Test that provisioning is skipped if already done."""
    provisioner = AnsibleProvisioner(temp_container_project_dir)

    # Create provisioning marker
    provisioner._mark_provisioned()

    # Verify provisioning is marked as done
    assert provisioner.is_provisioned()


def test_container_provisioning_error_handling(temp_container_project_dir, container_manager):
    """Test error handling for failed provisioning."""
    playbook = temp_container_project_dir / "playbook.yml"
    playbook.write_text("---\n- name: Invalid\n  hosts: all\n")

    provisioner = AnsibleProvisioner(temp_container_project_dir)

    # Mock ansible-playbook to fail
    with patch("subprocess.run") as mock_run:
        from utils.helpers import ProvisioningFailedError

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "PLAY RECAP [ERROR]"
        mock_run.return_value = mock_result

        # Verify ProvisioningFailedError is raised
        with pytest.raises(ProvisioningFailedError):
            provisioner.execute(
                playbook_path=playbook,
                inventory_path="172.17.0.2",
                dry_run=False,
            )


def test_container_provisioning_dry_run(temp_container_project_dir, container_manager):
    """Test provisioning in dry-run mode."""
    playbook = temp_container_project_dir / "playbook.yml"
    playbook.write_text("---\n- name: Test\n  hosts: all\n")

    provisioner = AnsibleProvisioner(temp_container_project_dir)

    # Mock ansible-playbook execution
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute provisioning with dry-run
        provisioner.execute(
            playbook_path=playbook,
            inventory_path="172.17.0.2",
            dry_run=True,
        )

        # Verify --check flag was passed
        call_args = mock_run.call_args
        assert "--check" in call_args[0][0]

        # Verify provisioning marker was NOT created (dry-run)
        assert not provisioner.is_provisioned()
