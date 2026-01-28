"""
Configuration Loader - YAML config file handling with environment variable support
"""

import os
import re
from pathlib import Path
import yaml
from dotenv import load_dotenv
from loguru import logger


def load_config(config_path: Path | str) -> dict:
    """
    Load configuration from YAML file.

    Supports environment variable substitution:
    - ${VAR_NAME} - replaced with environment variable value
    - ${VAR_NAME:-default} - replaced with env var or default if not set

    Args:
        config_path: Path to config.yaml file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    # Load .env file from same directory as config
    config_path = Path(config_path)
    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment from {env_path}")

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Copy config.yaml.example to config.yaml and update values."
        )

    try:
        with open(config_path, "r") as f:
            raw_content = f.read()
    except Exception as e:
        raise ValueError(f"Cannot read config file: {e}")

    # Substitute environment variables
    processed_content = _substitute_env_vars(raw_content)

    try:
        config = yaml.safe_load(processed_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    # Validate required sections
    required = ["plc", "sql"]
    for section in required:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Validate PLC config
    if "ip" not in config["plc"]:
        raise ValueError("Missing required config: plc.ip")

    # Validate SQL config
    if "connection_string" not in config["sql"]:
        raise ValueError("Missing required config: sql.connection_string")

    logger.info(f"Configuration loaded from {config_path}")
    return config


def _substitute_env_vars(content: str) -> str:
    """
    Replace ${VAR_NAME} and ${VAR_NAME:-default} with environment variable values.

    Args:
        content: Raw config file content

    Returns:
        Content with environment variables substituted
    """
    # Pattern: ${VAR_NAME} or ${VAR_NAME:-default}
    pattern = r'\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}'

    def replace_match(match):
        var_name = match.group(1)
        default_value = match.group(2)

        value = os.getenv(var_name)
        if value is not None:
            return value
        elif default_value is not None:
            return default_value
        else:
            logger.warning(f"Environment variable {var_name} not set and no default provided")
            return ""

    return re.sub(pattern, replace_match, content)
