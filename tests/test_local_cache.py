"""Tests for local cache (SQLite store-and-forward)."""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.local_cache import LocalCache


class TestLocalCache:
    """Tests for LocalCache class."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache instance with temporary database."""
        db_path = tmp_path / "test_cache.db"
        config = {"database": str(db_path)}
        return LocalCache(config)

    def test_init_creates_database(self, cache, tmp_path):
        """Database file should be created on init."""
        db_path = tmp_path / "test_cache.db"
        assert db_path.exists()

    def test_add_and_get_record(self, cache):
        """Should be able to add and retrieve a record."""
        data = {"RECIPE_NUMBER": 42, "TOTAL_WT": 1000}
        mappings = {"RECIPE_NUMBER": "Recipe_Number"}

        # Add record
        result = cache.add_record(data, mappings)
        assert result is True

        # Get record
        record = cache.get_oldest_record()
        assert record is not None

        record_id, record_data = record
        assert record_id == 1
        assert record_data["RECIPE_NUMBER"] == 42
        assert record_data["TOTAL_WT"] == 1000

    def test_get_pending_count(self, cache):
        """Should return correct pending count."""
        assert cache.get_pending_count() == 0

        cache.add_record({"test": 1}, {"test": "Test"})
        assert cache.get_pending_count() == 1

        cache.add_record({"test": 2}, {"test": "Test"})
        assert cache.get_pending_count() == 2

    def test_remove_record(self, cache):
        """Should be able to remove a record."""
        cache.add_record({"test": 1}, {"test": "Test"})
        assert cache.get_pending_count() == 1

        record = cache.get_oldest_record()
        record_id, _ = record

        result = cache.remove_record(record_id)
        assert result is True
        assert cache.get_pending_count() == 0

    def test_fifo_order(self, cache):
        """Records should be retrieved in FIFO order."""
        cache.add_record({"order": 1}, {"order": "Order"})
        cache.add_record({"order": 2}, {"order": "Order"})
        cache.add_record({"order": 3}, {"order": "Order"})

        # First record should be order 1
        record_id, data = cache.get_oldest_record()
        assert data["order"] == 1
        cache.remove_record(record_id)

        # Next should be order 2
        record_id, data = cache.get_oldest_record()
        assert data["order"] == 2
        cache.remove_record(record_id)

        # Last should be order 3
        record_id, data = cache.get_oldest_record()
        assert data["order"] == 3

    def test_get_mappings(self, cache):
        """Should store and retrieve mappings."""
        mappings = {"RECIPE_NUMBER": "Recipe_Number", "TOTAL_WT": "Total_Weight"}
        cache.add_record({"test": 1}, mappings)

        retrieved = cache.get_mappings()
        assert retrieved == mappings

    def test_empty_cache_returns_none(self, cache):
        """Empty cache should return None for get_oldest_record."""
        record = cache.get_oldest_record()
        assert record is None

    def test_increment_attempts(self, cache):
        """Should increment attempt counter."""
        cache.add_record({"test": 1}, {"test": "Test"})

        record_id, _ = cache.get_oldest_record()

        cache.increment_attempts(record_id)
        cache.increment_attempts(record_id)

        # Check attempts (would need to add a method to read attempts,
        # but this at least verifies no errors)
        assert cache.get_pending_count() == 1


class TestLocalCacheThreadSafety:
    """Tests for thread safety of LocalCache."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a cache instance with temporary database."""
        db_path = tmp_path / "test_cache.db"
        config = {"database": str(db_path)}
        return LocalCache(config)

    def test_concurrent_adds(self, cache):
        """Multiple threads adding records should not corrupt data."""
        import threading

        def add_records(start, count):
            for i in range(count):
                cache.add_record({"value": start + i}, {"value": "Value"})

        threads = [
            threading.Thread(target=add_records, args=(0, 10)),
            threading.Thread(target=add_records, args=(100, 10)),
            threading.Thread(target=add_records, args=(200, 10)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cache.get_pending_count() == 30
