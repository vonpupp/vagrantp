"""Unit tests for Ansible provisioning orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from provision.ansible import AnsibleProvisioner
from utils.helpers import ProvisioningFailedError, VagrantpError


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def provisioner(temp_project_dir):
    """Create Ansible provisioner for testing."""
    return AnsibleProvisioner(temp_project_dir)


@pytest.fixture
def test_playbook(temp_project_dir):
    """Create a test Ansible playbook."""
    playbook = temp_project_dir / "playbook.yml"
    playbook.write_text("""---
- name: Test playbook
  hosts: all
  become: yes
  tasks:
    - name: Update package cache
      package:
        update_cache: yes
    - name: Install base packages
      package:
        name:
          - git
          - vim
          - tmux
        state: present
""")
    return playbook


@pytest.fixture
def test_vars_file(temp_project_dir):
    """Create a test Ansible variables file."""
    vars_file = temp_project_dir / "vars.yml"
    vars_file.write_text("""
packages:
  - git
  - vim
  - tmux
""")
    return vars_file


def test_ansible_provisioner_init(provisioner, temp_project_dir):
    """Test that Ansible provisioner initializes correctly."""
    assert provisioner.project_dir == temp_project_dir
    assert provisioner.provisioning_marker == temp_project_dir / ".provisioned"


def test_execute_provisioning_success(provisioner, test_playbook):
    """Test successful playbook execution."""
    with patch("provision.ansible.run_command") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "PLAY [all]"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            dry_run=False,
        )

        # Verify run_command was called
        assert mock_run.called

        # Verify provisioning marker was created
        assert provisioner.is_provisioned()


def test_execute_provisioning_with_vars_file(provisioner, test_playbook, test_vars_file):
    """Test playbook execution with variables file."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            vars_path=test_vars_file,
            dry_run=False,
        )

        # Verify variables file was passed
        call_args = mock_run.call_args[0][0]
        assert "-e" in call_args
        assert f"@{test_vars_file}" in call_args


def test_execute_provisioning_with_extra_vars(provisioner, test_playbook):
    """Test playbook execution with extra variables."""
    extra_vars = {"var1": "value1", "var2": "value2"}

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            extra_vars=extra_vars,
            dry_run=False,
        )

        # Verify extra vars were passed
        call_args = mock_run.call_args[0][0]
        assert "-e" in call_args
        assert "var1=value1" in call_args
        assert "var2=value2" in call_args


def test_execute_provisioning_dry_run(provisioner, test_playbook):
    """Test playbook execution in dry-run mode."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            dry_run=True,
        )

        # Verify --check flag was passed
        call_args = mock_run.call_args[0][0]
        assert "--check" in call_args

        # Verify provisioning marker was NOT created
        assert not provisioner.is_provisioned()


def test_execute_provisioning_failure(provisioner, test_playbook):
    """Test handling of failed playbook execution."""
    call_count = [0]

    def mock_run_side_effect(*args, **kwargs):
        call_count[0] += 1
        mock_result = MagicMock()
        # First call is SSH verification, second call is playbook execution
        if call_count[0] == 1:
            mock_result.returncode = 0
            mock_result.stdout = "all | SUCCESS => {"
            mock_result.stderr = ""
        else:
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "PLAY RECAP [ERROR]"
        return mock_result

    with patch("provision.ansible.run_command") as mock_run:
        mock_run.side_effect = mock_run_side_effect

        with pytest.raises(ProvisioningFailedError) as exc_info:
            provisioner.execute(
                playbook_path=test_playbook,
                inventory_path="192.168.1.100",
                dry_run=False,
            )

        # Verify error message
        assert "Playbook execution failed" in str(exc_info.value)
        assert "exit code 1" in str(exc_info.value)

        # Verify provisioning marker was NOT created
        assert not provisioner.is_provisioned()


def test_execute_provisioning_missing_playbook(provisioner, temp_project_dir):
    """Test error when playbook doesn't exist."""
    missing_playbook = temp_project_dir / "missing.yml"

    with pytest.raises(ProvisioningFailedError) as exc_info:
        provisioner.execute(
            playbook_path=missing_playbook,
            inventory_path="192.168.1.100",
            dry_run=False,
        )

    assert "Playbook not found" in str(exc_info.value)


def test_execute_provisioning_missing_vars_file(provisioner, test_playbook, temp_project_dir):
    """Test error when vars file doesn't exist."""
    missing_vars = temp_project_dir / "missing.yml"

    with pytest.raises(ProvisioningFailedError) as exc_info:
        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            vars_path=missing_vars,
            dry_run=False,
        )

    assert "Variables file not found" in str(exc_info.value)


def test_verify_ssh_connection_success(provisioner):
    """Test successful SSH connection verification."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "all | SUCCESS => {"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Should not raise any exception
        provisioner._verify_ssh_connection("192.168.1.100")

        # Verify ansible ping was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "ansible" in call_args
        assert "ping" in call_args
        assert "-i" in call_args
        assert "192.168.1.100" in call_args


def test_verify_ssh_connection_failure(provisioner):
    """Test handling of SSH connection failure."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "Connection refused"
        mock_run.return_value = mock_result

        with pytest.raises(VagrantpError) as exc_info:
            provisioner._verify_ssh_connection("192.168.1.100")

        # Verify error message
        assert "SSH connection verification failed" in str(exc_info.value.message)


def test_mark_provisioned(provisioner, temp_project_dir):
    """Test marking infrastructure as provisioned."""
    assert not provisioner.is_provisioned()

    provisioner._mark_provisioned()

    assert provisioner.is_provisioned()
    marker = temp_project_dir / ".provisioned"
    assert marker.exists()


def test_is_provisioned(provisioner, temp_project_dir):
    """Test checking if infrastructure is provisioned."""
    # Initially not provisioned
    assert not provisioner.is_provisioned()

    # Create marker file
    marker = temp_project_dir / ".provisioned"
    marker.write_text("test")

    # Now should be provisioned
    assert provisioner.is_provisioned()


def test_clear_provisioning_marker(provisioner, temp_project_dir):
    """Test clearing provisioning marker."""
    # Create marker
    marker = temp_project_dir / ".provisioned"
    marker.write_text("test")

    assert provisioner.is_provisioned()

    # Clear marker
    provisioner.clear_provisioning_marker()

    assert not provisioner.is_provisioned()
    assert not marker.exists()


def test_idempotency_skip_provisioning(provisioner, test_playbook):
    """Test that provisioning is skipped when already done."""
    # Mark as provisioned
    provisioner._mark_provisioned()

    # Mock successful SSH verification
    with patch("provision.ansible.run_command") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "all | SUCCESS => {"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute provisioning
        # Note: idempotency check is in CLI, not in provisioner
        # This test verifies the marker mechanism
        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            dry_run=False,
        )

        # Verify provisioning marker still exists
        assert provisioner.is_provisioned()


def test_execute_command_structure(provisioner, test_playbook):
    """Test that ansible-playbook command is built correctly."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        provisioner.execute(
            playbook_path=test_playbook,
            inventory_path="192.168.1.100",
            dry_run=False,
        )

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ansible-playbook"
        assert str(test_playbook) in call_args
        assert "-i" in call_args
        assert "192.168.1.100" in call_args
