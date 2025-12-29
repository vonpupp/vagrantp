"""Unit tests for container manager."""

from unittest.mock import Mock, patch

import pytest

from podman.container_manager import ContainerManager
from utils.helpers import (
    InfrastructureState,
    VagrantpError,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_container_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def container_manager(temp_project_dir):
    """Create container manager for testing."""
    return ContainerManager("test_container", temp_project_dir)


class TestContainerManager:
    """Tests for ContainerManager class."""

    def test_initialization(self, temp_project_dir):
        """Test container manager initialization."""
        manager = ContainerManager("test_container", temp_project_dir)

        assert manager.infra_id == "test_container"
        assert manager.project_dir == temp_project_dir

    def test_initialization_default_project_dir(self, tmp_path):
        """Test container manager initialization with default project directory."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            manager = ContainerManager("test_container")
            assert manager.project_dir == tmp_path

    @patch("podman.container_manager.run_command")
    def test_create_checks_podman_availability(self, mock_run_command, container_manager):
        """Test that create checks for Podman availability."""
        mock_run_command.side_effect = Exception("Podman not found")

        config = {"MEMORY": "512", "CPUS": "1", "IMAGE": "alpine:latest"}

        with pytest.raises(Exception):
            container_manager.create(config)

        mock_run_command.assert_called_with(["podman", "--version"])

    @patch("podman.container_manager.run_command")
    def test_create_success(self, mock_run_command, container_manager):
        """Test that create executes successfully."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result

        config = {"MEMORY": "512", "CPUS": "1", "IMAGE": "alpine:latest"}

        container_manager.create(config)

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "podman"

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_connect_checks_state(self, mock_get_state, mock_run_command, container_manager):
        """Test that connect checks infrastructure state."""
        mock_get_state.return_value = InfrastructureState.STOPPED

        with pytest.raises(VagrantpError) as exc_info:
            container_manager.connect()

        assert "not running" in str(exc_info.value)

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_connect_executes_ssh(self, mock_get_state, mock_run_command, container_manager):
        """Test that connect executes podman exec command."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.connect("echo test")

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "podman"
        assert call_args[1] == "exec"
        assert call_args[2] == "-it"
        assert call_args[3] == "test_container"
        assert "/bin/sh" in call_args

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_connect_interactive(self, mock_get_state, mock_run_command, container_manager):
        """Test that connect in interactive mode without command."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.connect()

        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "podman"
        assert call_args[1] == "exec"
        assert "-it" in call_args

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_stop_checks_state(self, mock_get_state, mock_run_command, container_manager):
        """Test that stop checks infrastructure state."""
        mock_get_state.return_value = InfrastructureState.NOT_CREATED

        container_manager.stop()

        mock_run_command.assert_not_called()

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_stop_graceful(self, mock_get_state, mock_run_command, container_manager):
        """Test graceful stop."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.stop(force=False)

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "podman"
        assert call_args[1] == "stop"
        assert "--force" not in call_args

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_stop_force(self, mock_get_state, mock_run_command, container_manager):
        """Test force stop."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.stop(force=True)

        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "podman"
        assert call_args[1] == "kill"
        assert "--force" not in call_args

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_remove_checks_state(self, mock_get_state, mock_run_command, container_manager):
        """Test that remove checks infrastructure state."""
        mock_get_state.return_value = InfrastructureState.NOT_CREATED

        container_manager.remove()

        mock_run_command.assert_not_called()

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_remove_force(self, mock_get_state, mock_run_command, container_manager):
        """Test force removal."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.remove(force=True)

        mock_run_command.assert_called()
        calls = mock_run_command.call_args_list

        kill_call = [c for c in calls if len(c[0][0]) > 1 and c[0][0][1] == "kill"]
        assert len(kill_call) > 0

        rm_call = [c for c in calls if len(c[0][0]) > 1 and c[0][0][1] == "rm"]
        assert len(rm_call) > 0

    @patch("podman.container_manager.run_command")
    @patch.object(ContainerManager, "_get_state")
    def test_remove_success(self, mock_get_state, mock_run_command, container_manager):
        """Test that remove sets infrastructure state correctly."""
        mock_get_state.return_value = InfrastructureState.RUNNING

        container_manager.remove(force=True)

        mock_run_command.assert_called()
        calls = mock_run_command.call_args_list
        assert len(calls) == 2

    def test_build_run_command_basic(self, container_manager):
        """Test building basic podman run command."""
        config = {"MEMORY": "1024", "CPUS": "2", "IMAGE": "alpine:latest"}

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
        assert "alpine:latest" in cmd

    def test_build_run_command_with_network(self, container_manager):
        """Test building podman run command with networking."""
        config = {"MEMORY": "512", "CPUS": "1", "NETWORK_MODE": "bridge"}

        cmd = container_manager._build_run_command(config)

        assert "--network" in cmd
        assert "bridge" in cmd

    def test_build_run_command_with_ports(self, container_manager):
        """Test building podman run command with port mappings."""
        config = {"MEMORY": "512", "CPUS": "1", "PORTS": "8080:80,auto:443"}

        cmd = container_manager._build_run_command(config)

        port_args = [arg for arg in cmd if arg == "-p" or ":" in arg]
        assert len(port_args) > 0
        assert "8080:80" in cmd or any("8080:80" in str(arg) for arg in cmd)
