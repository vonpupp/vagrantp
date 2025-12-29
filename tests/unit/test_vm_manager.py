"""Unit tests for VM manager."""

import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
from vagrant.vm_manager import VMManager
from utils.helpers import (
    InfrastructureState,
    VagrantpError,
    ProviderNotAvailableError,
    ErrorCode,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def vm_manager(temp_project_dir):
    """Create VM manager for testing."""
    return VMManager("test_vm", temp_project_dir)


class TestVMManager:
    """Tests for VMManager class."""

    def test_initialization(self, temp_project_dir):
        """Test VM manager initialization."""
        manager = VMManager("test_vm", temp_project_dir)

        assert manager.infra_id == "test_vm"
        assert manager.project_dir == temp_project_dir
        assert manager.vagrantfile_path == temp_project_dir / "Vagrantfile"
        assert manager.state_manager is not None

    def test_initialization_default_project_dir(self, tmp_path):
        """Test VM manager initialization with default project directory."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            manager = VMManager("test_vm")
            assert manager.project_dir == tmp_path

    @patch("vagrant.vm_manager.run_command")
    def test_create_checks_vagrant_availability(self, mock_run_command, vm_manager):
        """Test that create checks for Vagrant availability."""
        mock_run_command.side_effect = Exception("Vagrant not found")

        config = {
            "PROVIDER": "virtualbox",
            "MEMORY": "1024",
            "CPUS": "1",
            "DISK_SIZE": "10G",
        }

        with pytest.raises(Exception):
            vm_manager.create(config)

        mock_run_command.assert_called_with(["vagrant", "--version"])

    @patch("vagrant.vm_manager.run_command")
    @patch("vagrant.vm_manager.run_command")
    def test_create_generates_vagrantfile(
        self, mock_run_command, vm_manager, temp_project_dir
    ):
        """Test that create generates Vagrantfile."""
        mock_run_command.return_value = Mock()

        config = {
            "PROVIDER": "virtualbox",
            "MEMORY": "2048",
            "CPUS": "2",
            "DISK_SIZE": "20G",
        }

        vm_manager.create(config)

        vagrantfile = temp_project_dir / "Vagrantfile"
        assert vagrantfile.exists()
        content = vagrantfile.read_text()
        assert 'Vagrant.configure("2")' in content
        assert "vb.memory = 2048" in content
        assert "vb.cpus = 2" in content

    @patch("vagrant.vm_manager.run_command")
    def test_create_sets_state(self, mock_run_command, vm_manager):
        """Test that create sets infrastructure state correctly."""
        mock_run_command.return_value = Mock()

        config = {
            "PROVIDER": "virtualbox",
            "MEMORY": "1024",
            "CPUS": "1",
            "DISK_SIZE": "10G",
        }

        initial_state = vm_manager.state_manager.get_state("test_vm")
        assert initial_state == InfrastructureState.NOT_CREATED

        vm_manager.create(config)

        final_state = vm_manager.state_manager.get_state("test_vm")
        assert final_state == InfrastructureState.RUNNING

    @patch("vagrant.vm_manager.run_command")
    def test_connect_checks_state(self, mock_run_command, vm_manager):
        """Test that connect checks infrastructure state."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.STOPPED)

        with pytest.raises(VagrantpError) as exc_info:
            vm_manager.connect()

        assert "not running" in str(exc_info.value)

    @patch("vagrant.vm_manager.run_command")
    def test_connect_executes_ssh(self, mock_run_command, vm_manager):
        """Test that connect executes SSH command."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.connect("echo test")

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "vagrant"
        assert call_args[1] == "ssh"
        assert call_args[2] == "-c"
        assert call_args[3] == "echo test"

    @patch("vagrant.vm_manager.run_command")
    def test_connect_interactive(self, mock_run_command, vm_manager):
        """Test that connect in interactive mode without command."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.connect()

        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "vagrant"
        assert call_args[1] == "ssh"
        assert len(call_args) == 2

    @patch("vagrant.vm_manager.run_command")
    def test_stop_checks_state(self, mock_run_command, vm_manager):
        """Test that stop checks infrastructure state."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.NOT_CREATED)

        vm_manager.stop()

        mock_run_command.assert_not_called()

    @patch("vagrant.vm_manager.run_command")
    def test_stop_graceful(self, mock_run_command, vm_manager):
        """Test graceful stop."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.stop(force=False)

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "vagrant"
        assert call_args[1] == "halt"
        assert "--force" not in call_args

    @patch("vagrant.vm_manager.run_command")
    def test_stop_force(self, mock_run_command, vm_manager):
        """Test force stop."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.stop(force=True)

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "vagrant"
        assert call_args[1] == "halt"
        assert "--force" in call_args

    @patch("vagrant.vm_manager.run_command")
    def test_remove_checks_state(self, mock_run_command, vm_manager):
        """Test that remove checks infrastructure state."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.NOT_CREATED)

        vm_manager.remove()

        mock_run_command.assert_not_called()

    @patch("vagrant.vm_manager.run_command")
    def test_remove_force(self, mock_run_command, vm_manager):
        """Test force removal."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.remove(force=True)

        mock_run_command.assert_called()
        calls = mock_run_command.call_args_list

        halt_call = [c for c in calls if c[0][0][1] == "halt"][0]
        assert halt_call[0][0][2] == "--force"

        destroy_call = [c for c in calls if c[0][0][1] == "destroy"][0]
        assert "--force" in destroy_call[0][0]

    @patch("vagrant.vm_manager.run_command")
    def test_remove_sets_state(self, mock_run_command, vm_manager):
        """Test that remove sets infrastructure state correctly."""
        vm_manager.state_manager.set_state("test_vm", InfrastructureState.RUNNING)

        vm_manager.remove(force=True)

        final_state = vm_manager.state_manager.get_state("test_vm")
        assert final_state == InfrastructureState.NOT_CREATED
