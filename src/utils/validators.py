"""
Data Validators - Recipe data sanity checks
"""

from loguru import logger


def validate_recipe_data(data: dict, validation_config: dict) -> tuple[bool, list[str]]:
    """
    Validate recipe data against configured limits.

    Args:
        data: Recipe data dictionary from PLC
        validation_config: Validation configuration with limits

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    limits = validation_config.get("limits", {})

    for field, field_limits in limits.items():
        if field not in data:
            continue

        value = data[field]

        # Skip None values
        if value is None:
            continue

        # Check min limit
        if "min" in field_limits:
            if value < field_limits["min"]:
                errors.append(
                    f"{field} value {value} is below minimum {field_limits['min']}"
                )

        # Check max limit
        if "max" in field_limits:
            if value > field_limits["max"]:
                errors.append(
                    f"{field} value {value} is above maximum {field_limits['max']}"
                )

    if errors:
        for error in errors:
            logger.warning(f"Validation: {error}")

    return (len(errors) == 0, errors)


def validate_config_limits(limits: dict) -> bool:
    """
    Validate that limit configuration is valid.

    Args:
        limits: Limits configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    for field, field_limits in limits.items():
        if "min" in field_limits and "max" in field_limits:
            if field_limits["min"] > field_limits["max"]:
                logger.error(f"Invalid limits for {field}: min > max")
                return False

    return True
