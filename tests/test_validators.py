"""Tests for data validators."""

import pytest
from src.utils.validators import validate_recipe_data, validate_config_limits


class TestValidateRecipeData:
    """Tests for validate_recipe_data function."""

    def test_valid_data_within_limits(self):
        """Data within limits should pass validation."""
        data = {
            "TOTAL_WT": 1000,
            "RECIPE_NUMBER": 50,
            "BATCH_RATIO": 1.0
        }
        validation_config = {
            "limits": {
                "TOTAL_WT": {"min": 0, "max": 50000},
                "RECIPE_NUMBER": {"min": 1, "max": 99},
                "BATCH_RATIO": {"min": 0, "max": 100}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is True
        assert len(errors) == 0

    def test_value_below_minimum(self):
        """Value below minimum should fail validation."""
        data = {"RECIPE_NUMBER": 0}
        validation_config = {
            "limits": {
                "RECIPE_NUMBER": {"min": 1, "max": 99}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is False
        assert len(errors) == 1
        assert "below minimum" in errors[0]

    def test_value_above_maximum(self):
        """Value above maximum should fail validation."""
        data = {"TOTAL_WT": 60000}
        validation_config = {
            "limits": {
                "TOTAL_WT": {"min": 0, "max": 50000}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is False
        assert len(errors) == 1
        assert "above maximum" in errors[0]

    def test_missing_field_ignored(self):
        """Fields not in data should be ignored."""
        data = {"OTHER_FIELD": 100}
        validation_config = {
            "limits": {
                "TOTAL_WT": {"min": 0, "max": 50000}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is True
        assert len(errors) == 0

    def test_none_value_ignored(self):
        """None values should be skipped."""
        data = {"TOTAL_WT": None}
        validation_config = {
            "limits": {
                "TOTAL_WT": {"min": 0, "max": 50000}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is True
        assert len(errors) == 0

    def test_empty_config(self):
        """Empty validation config should pass all data."""
        data = {"TOTAL_WT": 999999}
        validation_config = {}

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is True
        assert len(errors) == 0

    def test_multiple_errors(self):
        """Multiple validation errors should all be reported."""
        data = {
            "TOTAL_WT": -100,
            "RECIPE_NUMBER": 200
        }
        validation_config = {
            "limits": {
                "TOTAL_WT": {"min": 0, "max": 50000},
                "RECIPE_NUMBER": {"min": 1, "max": 99}
            }
        }

        is_valid, errors = validate_recipe_data(data, validation_config)

        assert is_valid is False
        assert len(errors) == 2


class TestValidateConfigLimits:
    """Tests for validate_config_limits function."""

    def test_valid_limits(self):
        """Valid limits should pass."""
        limits = {
            "TOTAL_WT": {"min": 0, "max": 50000},
            "RECIPE_NUMBER": {"min": 1, "max": 99}
        }

        result = validate_config_limits(limits)

        assert result is True

    def test_min_greater_than_max(self):
        """Min > max should fail."""
        limits = {
            "TOTAL_WT": {"min": 50000, "max": 0}
        }

        result = validate_config_limits(limits)

        assert result is False

    def test_only_min_or_max(self):
        """Having only min or max should be valid."""
        limits = {
            "TOTAL_WT": {"min": 0},
            "RECIPE_NUMBER": {"max": 99}
        }

        result = validate_config_limits(limits)

        assert result is True

    def test_empty_limits(self):
        """Empty limits should be valid."""
        result = validate_config_limits({})

        assert result is True
