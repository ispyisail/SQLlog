"""Tests for configuration loader."""

import pytest
import tempfile
import os
from pathlib import Path

from src.utils.config import load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path):
        """Valid config file should load successfully."""
        config_content = """
plc:
  ip: "192.168.50.10"
  slot: 0

sql:
  connection_string: "Driver={ODBC Driver 18};Server=SVR;Database=Test"
  table: "dbo.Test"

mappings:
  RECIPE_NUMBER: "Recipe_Number"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config["plc"]["ip"] == "192.168.50.10"
        assert config["plc"]["slot"] == 0
        assert "connection_string" in config["sql"]
        assert config["mappings"]["RECIPE_NUMBER"] == "Recipe_Number"

    def test_missing_file_raises_error(self, tmp_path):
        """Missing config file should raise FileNotFoundError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(config_file)

        assert "Config file not found" in str(exc_info.value)

    def test_missing_plc_section_raises_error(self, tmp_path):
        """Missing plc section should raise ValueError."""
        config_content = """
sql:
  connection_string: "test"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)

        assert "Missing required config section: plc" in str(exc_info.value)

    def test_missing_sql_section_raises_error(self, tmp_path):
        """Missing sql section should raise ValueError."""
        config_content = """
plc:
  ip: "192.168.50.10"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)

        assert "Missing required config section: sql" in str(exc_info.value)

    def test_missing_plc_ip_raises_error(self, tmp_path):
        """Missing plc.ip should raise ValueError."""
        config_content = """
plc:
  slot: 0

sql:
  connection_string: "test"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)

        assert "Missing required config: plc.ip" in str(exc_info.value)

    def test_missing_connection_string_raises_error(self, tmp_path):
        """Missing sql.connection_string should raise ValueError."""
        config_content = """
plc:
  ip: "192.168.50.10"

sql:
  table: "test"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)

        assert "Missing required config: sql.connection_string" in str(exc_info.value)

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Invalid YAML should raise ValueError."""
        config_content = """
plc:
  ip: "test
  broken: yaml
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)

        assert "Invalid YAML" in str(exc_info.value)
