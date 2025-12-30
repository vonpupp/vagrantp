"""Unit tests for Ansible provisioning orchestrator."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from provision.ansible import ProvisioningManager
from utils.helpers import ProvisioningFailedError, VagrantpError


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def provision_manager(temp_project_dir):
    """Create provisioning manager fixture."""
    return ProvisioningManager("test-infra", temp_project_dir)


class TestProvisioningManager:
    """Tests for ProvisioningManager class."""

    def test_init(self, temp_project_dir):
        """Test initialization."""
        manager = ProvisioningManager("test-infra", temp_project_dir)
        assert manager.infra_id == "test-infra"
        assert manager.project_dir == temp_project_dir

    def test_init_default_project_dir(self):
        """Test initialization with default project directory."""
        manager = ProvisioningManager("test-infra")
        assert manager.project_dir == Path.cwd()

    @patch("provision.ansible.run_command")
    def test_execute_success(self, mock_run_command, provision_manager, temp_project_dir):
        """Test successful playbook execution."""
        # Create playbook
        playbook = temp_project_dir / "playbook.yml"
        playbook.write_text("---\n- hosts: all\n  tasks: []")

        # Mock ansible version check
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ansible", "--version"], 0, "", ""
        )

        # Mock Popen for playbook execution
        mock_process = MagicMock()
        mock_process.stdout = iter(["TASK [Test task]\n", "ok: [host]\n", "\n"])
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process):
            provision_manager.execute(str(playbook), inventory="test-host,")

    @patch("provision.ansible.run_command")
    def test_execute_playbook_not_found(self, mock_run_command, provision_manager):
        """Test error when playbook not found."""
        # Mock ansible version check
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ansible", "--version"], 0, "", ""
        )

        with pytest.raises(ProvisioningFailedError) as exc_info:
            provision_manager.execute("/nonexistent/playbook.yml")

        assert "Playbook not found" in str(exc_info.value)

    @patch("provision.ansible.run_command")
    def test_execute_ansible_not_installed(
        self, mock_run_command, provision_manager, temp_project_dir
    ):
        """Test error when Ansible not installed."""
        # Create playbook
        playbook = temp_project_dir / "playbook.yml"
        playbook.write_text("---\n- hosts: all\n  tasks: []")

        # Mock ansible version check to fail
        mock_run_command.side_effect = subprocess.CalledProcessError(1, ["ansible", "--version"])

        with pytest.raises(ProvisioningFailedError) as exc_info:
            provision_manager.execute(str(playbook), inventory="test-host,")

        assert "Ansible is not installed" in str(exc_info.value)

    @patch("provision.ansible.run_command")
    def test_execute_playbook_failure(self, mock_run_command, provision_manager, temp_project_dir):
        """Test error when playbook execution fails."""
        # Create playbook
        playbook = temp_project_dir / "playbook.yml"
        playbook.write_text("---\n- hosts: all\n  tasks: []")

        # Mock ansible version check
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ansible", "--version"], 0, "", ""
        )

        # Mock Popen to return non-zero exit code
        mock_process = MagicMock()
        mock_process.stdout = iter(["TASK [Test task]\n", "FAILED => [error]\n"])
        mock_process.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_process):
            with pytest.raises(ProvisioningFailedError) as exc_info:
                provision_manager.execute(str(playbook), inventory="test-host,")

            assert "Playbook execution failed" in str(exc_info.value)

    @patch("provision.ansible.run_command")
    def test_execute_dry_run(self, mock_run_command, provision_manager, temp_project_dir):
        """Test dry-run mode."""
        # Create playbook
        playbook = temp_project_dir / "playbook.yml"
        playbook.write_text("---\n- hosts: all\n  tasks: []")

        # Mock ansible version check
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ansible", "--version"], 0, "", ""
        )

        # Mock Popen
        mock_process = MagicMock()
        mock_process.stdout = iter(["TASK [Test task]\n", "ok: [host]\n", "\n"])
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process
            provision_manager.execute(str(playbook), inventory="test-host,", dry_run=True)

            # Verify --check flag was added
            args = mock_popen.call_args[0][0]
            assert "--check" in args

    @patch("provision.ansible.run_command")
    def test_execute_with_extra_vars(self, mock_run_command, provision_manager, temp_project_dir):
        """Test playbook execution with extra variables."""
        # Create playbook
        playbook = temp_project_dir / "playbook.yml"
        playbook.write_text("---\n- hosts: all\n  tasks: []")

        # Mock ansible version check
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ansible", "--version"], 0, "", ""
        )

        # Mock Popen
        mock_process = MagicMock()
        mock_process.stdout = iter(["TASK [Test task]\n", "ok: [host]\n", "\n"])
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_process
            provision_manager.execute(
                str(playbook),
                inventory="test-host,",
                extra_vars="var1=value1,var2=value2",
            )

            # Verify --extra-vars flag was added
            args = mock_popen.call_args[0][0]
            assert "--extra-vars" in args
            assert "var1=value1,var2=value2" in args

    @patch("provision.ansible.run_command")
    def test_verify_ssh_connection_success(self, mock_run_command, provision_manager):
        """Test successful SSH connection verification."""
        # Mock SSH command
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ssh", "test-host"],
            0,
            "connection_ok",
            "",
        )

        result = provision_manager.verify_ssh_connection("test-host")

        assert result is True

    @patch("provision.ansible.run_command")
    def test_verify_ssh_connection_failure(self, mock_run_command, provision_manager):
        """Test SSH connection verification failure."""
        # Mock SSH command to fail
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ssh", "test-host"],
            1,
            "Connection refused",
            "",
        )

        with pytest.raises(VagrantpError) as exc_info:
            provision_manager.verify_ssh_connection("test-host")

        assert "SSH connection failed" in str(exc_info.value)

    @patch("provision.ansible.run_command")
    def test_verify_ssh_connection_with_key(self, mock_run_command, provision_manager):
        """Test SSH connection verification with custom key."""
        # Mock SSH command
        mock_run_command.return_value = subprocess.CompletedProcess(
            ["ssh", "test-host"],
            0,
            "connection_ok",
            "",
        )

        result = provision_manager.verify_ssh_connection("test-host", ssh_key="/path/to/key")

        assert result is True

    def test_check_provisioning_status_not_provisioned(self, provision_manager):
        """Test checking provisioning status when not provisioned."""
        result = provision_manager.check_provisioning_status()
        assert result is False

    def test_check_provisioning_status_provisioned(self, provision_manager):
        """Test checking provisioning status when provisioned."""
        # Create state file
        state_file = provision_manager.project_dir / ".vagrantp_provisioned"
        state_file.write_text("123456789")

        result = provision_manager.check_provisioning_status()
        assert result is True

    def test_mark_provisioned(self, provision_manager):
        """Test marking infrastructure as provisioned."""
        provision_manager.mark_provisioned()

        state_file = provision_manager.project_dir / ".vagrantp_provisioned"
        assert state_file.exists()

    def test_clear_provisioned_status(self, provision_manager):
        """Test clearing provisioning status."""
        # Create state file
        state_file = provision_manager.project_dir / ".vagrantp_provisioned"
        state_file.write_text("123456789")

        # Clear status
        provision_manager.clear_provisioned_status()

        assert not state_file.exists()

    def test_clear_provisioned_status_when_not_provisioned(self, provision_manager):
        """Test clearing provisioning status when not provisioned."""
        # Should not raise error
        provision_manager.clear_provisioned_status()
