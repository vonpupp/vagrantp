"""Unit tests for configuration parser."""

import pytest
from pathlib import Path
from config.parser import ConfigurationParser, ValidationError, ValidationResult


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("""INFRA_TYPE=vm
PROVIDER=virtualbox
MEMORY=2048
CPUS=2
DISK_SIZE=20G
""")
    return env_file


@pytest.fixture
def parser(temp_env_file):
    """Create configuration parser with temp .env file."""
    return ConfigurationParser(temp_env_file)


class TestConfigurationParser:
    """Tests for ConfigurationParser class."""

    def test_load_env_file(self, parser, temp_env_file):
        """Test loading .env file."""
        config = parser.load()

        assert config.get("INFRA_TYPE") == "vm"
        assert config.get("PROVIDER") == "virtualbox"
        assert config.get("MEMORY") == "2048"
        assert config.get("CPUS") == "2"
        assert config.get("DISK_SIZE") == "20G"

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading non-existent .env file."""
        parser = ConfigurationParser(tmp_path / "nonexistent.env")

        with pytest.raises(FileNotFoundError):
            parser.load()

    def test_get_existing_key(self, parser):
        """Test getting existing configuration value."""
        parser.load()
        value = parser.get("INFRA_TYPE")
        assert value == "vm"

    def test_get_nonexistent_key(self, parser):
        """Test getting non-existent configuration value."""
        parser.load()
        value = parser.get("NONEXISTENT")
        assert value is None

    def test_get_with_default(self, parser):
        """Test getting value with default."""
        parser.load()
        value = parser.get("NONEXISTENT", "default_value")
        assert value == "default_value"

    def test_get_int(self, parser):
        """Test getting integer value."""
        parser.load()
        value = parser.get_int("CPUS")
        assert value == 2

    def test_get_int_invalid(self, parser):
        """Test getting invalid integer value."""
        parser.load()
        value = parser.get_int("NONEXISTENT", 5)
        assert value == 5

    def test_get_bool_true(self, tmp_path):
        """Test getting boolean true value."""
        env_file = tmp_path / ".env"
        env_file.write_text("ENABLED=true\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        value = parser.get_bool("ENABLED")
        assert value is True

    def test_get_bool_false(self, tmp_path):
        """Test getting boolean false value."""
        env_file = tmp_path / ".env"
        env_file.write_text("ENABLED=false\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        value = parser.get_bool("ENABLED")
        assert value is False

    def test_parse_memory_bytes(self, parser):
        """Test parsing memory value in bytes."""
        parser.load()

        memory_mb = parser._parse_memory("1024")
        assert memory_mb == 1024

    def test_parse_memory_gb(self, parser):
        """Test parsing memory value in GB."""
        parser.load()

        memory_mb = parser._parse_memory("2G")
        assert memory_mb == 2048

    def test_parse_memory_mb(self, parser):
        """Test parsing memory value in MB."""
        parser.load()

        memory_mb = parser._parse_memory("1024M")
        assert memory_mb == 1024

    def test_parse_memory_invalid(self, parser):
        """Test parsing invalid memory value."""
        parser.load()

        with pytest.raises(ValidationError) as exc_info:
            parser._parse_memory("invalid")

        assert exc_info.value.field == "MEMORY"

    def test_parse_disk_size_gb(self, parser):
        """Test parsing disk size in GB."""
        parser.load()

        disk_gb = parser._parse_disk_size("20G")
        assert disk_gb == 20

    def test_parse_disk_size_mb(self, parser):
        """Test parsing disk size in MB."""
        parser.load()

        disk_gb = parser._parse_disk_size("10240M")
        assert disk_gb == 10

    def test_parse_ports(self, parser):
        """Test parsing port mappings."""
        parser.load()

        ports = parser._parse_ports("8080:80,auto:443")

        assert len(ports) == 2
        assert ports[0]["host"] == 8080
        assert ports[0]["container"] == 80
        assert ports[0]["auto"] is False
        assert ports[1]["host"] == 0
        assert ports[1]["container"] == 443
        assert ports[1]["auto"] is True

    def test_validate_required_fields(self, parser):
        """Test validation of required fields."""
        parser.load()

        result = parser.validate()
        assert result.valid is True

    def test_validate_missing_infra_type(self, tmp_path):
        """Test validation with missing INFRA_TYPE."""
        env_file = tmp_path / ".env"
        env_file.write_text("PROVIDER=virtualbox\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("INFRA_TYPE is required" in e for e in result.errors)

    def test_validate_invalid_infra_type(self, tmp_path):
        """Test validation with invalid INFRA_TYPE."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=docker\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("INFRA_TYPE must be 'vm' or 'container'" in e for e in result.errors)

    def test_validate_missing_provider_for_vm(self, tmp_path):
        """Test validation with missing PROVIDER for VM."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=vm\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("PROVIDER is required for VM" in e for e in result.errors)

    def test_validate_memory_minimum(self, tmp_path):
        """Test validation with insufficient MEMORY."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=vm\nPROVIDER=virtualbox\nMEMORY=256\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("MEMORY must be at least 512MB" in e for e in result.errors)

    def test_validate_cpus_minimum(self, tmp_path):
        """Test validation with insufficient CPUS."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=vm\nPROVIDER=virtualbox\nCPUS=0\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("CPUS must be at least 1" in e for e in result.errors)

    def test_validate_disk_size_minimum(self, tmp_path):
        """Test validation with insufficient DISK_SIZE."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=vm\nPROVIDER=virtualbox\nDISK_SIZE=1G\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("DISK_SIZE must be at least 5GB" in e for e in result.errors)

    def test_validate_invalid_ipv4(self, tmp_path):
        """Test validation with invalid IPv4 address."""
        env_file = tmp_path / ".env"
        env_file.write_text("INFRA_TYPE=vm\nPROVIDER=virtualbox\nIP_ADDRESS=invalid\n")
        parser = ConfigurationParser(env_file)
        parser.load()

        result = parser.validate()
        assert result.valid is False
        assert any("Invalid IP_ADDRESS format" in e for e in result.errors)
