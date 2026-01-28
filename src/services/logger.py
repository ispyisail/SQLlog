"""
Logger Configuration - loguru setup with rotation
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(config: dict):
    """
    Configure loguru with rotation and retention.

    Args:
        config: Logging configuration dict with keys:
            - directory: Log directory path
            - rotation: Rotation size (e.g., "10 MB")
            - retention: Retention period (e.g., "30 days")
            - level: Log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    log_dir = Path(config.get("directory", "logs"))
    log_dir.mkdir(exist_ok=True)

    rotation = config.get("rotation", "10 MB")
    retention = config.get("retention", "30 days")
    level = config.get("level", "INFO")

    # Console handler
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # File handler - all logs
    logger.add(
        log_dir / "sqllog.log",
        level=level,
        rotation=rotation,
        retention=retention,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    # File handler - errors only
    logger.add(
        log_dir / "error.log",
        level="ERROR",
        rotation=rotation,
        retention=retention,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    logger.info("Logger initialized")
    return logger
