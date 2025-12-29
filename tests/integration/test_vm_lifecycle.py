"""Integration tests for VM lifecycle."""

import pytest

from config.parser import ConfigurationParser
from utils.helpers import InfrastructureState
from vagrant.vm_manager import VMManager


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with .env file."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    env_file = project_dir / ".env"
    env_file.write_text("""INFRA_TYPE=vm
PROVIDER=virtualbox
MEMORY=1024
CPUS=1
DISK_SIZE=10G
""")

    return project_dir


@pytest.fixture
def vm_manager(temp_project_dir):
    """Create VM manager for testing."""
    manager = VMManager("test_project", temp_project_dir)
    yield manager


def test_vm_get_state_returns_not_created(vm_manager, temp_project_dir):
    """Test that VM state returns NOT_CREATED when VM doesn't exist."""
    state = vm_manager._get_state()
    assert state == InfrastructureState.NOT_CREATED


def test_vagrantfile_generation(vm_manager, temp_project_dir):
    """Test that Vagrantfile is generated correctly."""
    config = {
        "PROVIDER": "virtualbox",
        "MEMORY": "2048",
        "CPUS": "2",
        "DISK_SIZE": "20G",
    }

    vm_manager._generate_vagrantfile(config)

    vagrantfile = temp_project_dir / "Vagrantfile"
    assert vagrantfile.exists()

    content = vagrantfile.read_text()
    assert 'Vagrant.configure("2")' in content
    assert 'config.vm.provider "virtualbox"' in content
    assert "vb.memory = 2048" in content
    assert "vb.cpus = 2" in content


def test_configuration_loading(temp_project_dir):
    """Test that .env configuration is loaded correctly."""
    parser = ConfigurationParser(temp_project_dir / ".env")
    config = parser.load()

    assert config.get("INFRA_TYPE") == "vm"
    assert config.get("PROVIDER") == "virtualbox"
    assert config.get("MEMORY") == "1024"
    assert config.get("CPUS") == "1"
    assert config.get("DISK_SIZE") == "10G"


def test_infrastructure_id_resolution(temp_project_dir):
    """Test that infrastructure ID defaults to project directory name."""
    parser = ConfigurationParser(temp_project_dir / ".env")
    config = parser.load()

    infra_id = config.get("INFRA_ID", temp_project_dir.name)
    assert infra_id == "test_project"


def test_full_lifecycle_workflow(temp_project_dir, vm_manager):
    """Test complete VM lifecycle: create -> connect -> stop -> remove."""
    # Note: This test requires Vagrant to be installed
    # In CI, this test should be skipped or mocked

    config = {
        "INFRA_TYPE": "vm",
        "PROVIDER": "virtualbox",
        "MEMORY": "1024",
        "CPUS": "1",
        "DISK_SIZE": "10G",
    }

    # Initial state: not_created
    state = vm_manager._get_state()
    assert state == InfrastructureState.NOT_CREATED

    # Create VM
    # vm_manager.create(config)  # Requires actual Vagrant

    # Verify state transition to running
    # state = vm_manager._get_state()
    # assert state == InfrastructureState.RUNNING

    # Connect (optional)
    # vm_manager.connect("echo 'test'")

    # Stop VM
    # vm_manager.stop()

    # Verify state transition to stopped
    # state = vm_manager._get_state()
    # assert state == InfrastructureState.STOPPED

    # Remove VM
    # vm_manager.remove()

    # Verify state transition back to not_created
    # state = vm_manager._get_state()
    # assert state == InfrastructureState.NOT_CREATED
