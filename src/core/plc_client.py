"""
PLC Client - Allen-Bradley Logix communication via pycomm3
"""

import threading
from pycomm3 import LogixDriver
from loguru import logger


class PLCClient:
    """Handles Ethernet/IP communication with Allen-Bradley Logix PLC."""

    def __init__(self, config: dict):
        self.ip = config["ip"]
        self.slot = config.get("slot", 0)
        self.trigger_tag = config.get("trigger_tag", "SQLlog_Trigger")
        self.heartbeat_tag = config.get("heartbeat_tag", "SQLlog_Heartbeat")
        self.error_code_tag = config.get("error_code_tag", "SQLlog_Error_Code")
        self.recipe_tag = config.get("recipe_tag", "RECIPE[0]")

        # Extra tags to read (sequence number, batch ratio, etc.)
        self.extra_tags = config.get("extra_tags", {})
        self.bulk_names = config.get("bulk_names", {})

        self._driver = None
        self._connected = False
        self._lock = threading.Lock()  # Thread safety for driver access

    def connect(self) -> bool:
        """Establish connection to PLC."""
        with self._lock:
            try:
                self._driver = LogixDriver(self.ip, slot=self.slot)
                self._driver.open()
                self._connected = True
                logger.info(f"Connected to PLC at {self.ip}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to PLC: {e}")
                self._connected = False
                return False

    def disconnect(self):
        """Close PLC connection."""
        with self._lock:
            if self._driver:
                try:
                    self._driver.close()
                except Exception:
                    pass
                self._driver = None
                self._connected = False
                logger.info("Disconnected from PLC")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def read_trigger(self) -> int | None:
        """Read the recipe trigger tag value."""
        return self._read_tag(self.trigger_tag)

    def write_trigger(self, value: int) -> bool:
        """Write to the recipe trigger tag."""
        return self._write_tag(self.trigger_tag, value)

    def read_recipe(self) -> dict | None:
        """Read the entire recipe UDT structure."""
        with self._lock:
            try:
                if not self._ensure_connected_unlocked():
                    return None
                result = self._driver.read(self.recipe_tag)
                if result.error:
                    logger.error(f"Error reading recipe: {result.error}")
                    return None
                return result.value
            except Exception as e:
                logger.error(f"Exception reading recipe: {e}")
                self._connected = False
                return None

    def read_extra_tags(self) -> dict:
        """
        Read additional tags defined in config (sequence number, batch ratio, etc.)

        Returns:
            Dictionary with tag values keyed by config name
        """
        result = {}

        # Read extra_tags
        for name, tag in self.extra_tags.items():
            value = self._read_tag(tag)
            if value is not None:
                result[name] = value

        # Read bulk ingredient names
        for name, tag in self.bulk_names.items():
            value = self._read_tag(tag)
            if value is not None:
                result[name] = value

        return result

    def read_all_recipe_data(self) -> dict | None:
        """
        Read recipe UDT and merge with extra tags.

        Returns:
            Complete recipe data dictionary or None on error
        """
        recipe = self.read_recipe()
        if recipe is None:
            return None

        # Merge extra tags
        extra = self.read_extra_tags()
        recipe.update(extra)

        return recipe

    def increment_heartbeat(self, current_value: int) -> bool:
        """Increment the heartbeat tag (wraps at 32767)."""
        new_value = (current_value + 1) % 32768
        return self._write_tag(self.heartbeat_tag, new_value)

    def read_heartbeat(self) -> int | None:
        """Read current heartbeat value."""
        return self._read_tag(self.heartbeat_tag)

    def write_error_code(self, code: int) -> bool:
        """Write error code to PLC."""
        return self._write_tag(self.error_code_tag, code)

    def _read_tag(self, tag: str):
        """Generic tag read with connection check and thread safety."""
        with self._lock:
            try:
                if not self._ensure_connected_unlocked():
                    return None
                result = self._driver.read(tag)
                if result.error:
                    logger.error(f"Error reading {tag}: {result.error}")
                    return None
                return result.value
            except Exception as e:
                logger.error(f"Exception reading {tag}: {e}")
                self._connected = False
                return None

    def _write_tag(self, tag: str, value) -> bool:
        """Generic tag write with connection check and thread safety."""
        with self._lock:
            try:
                if not self._ensure_connected_unlocked():
                    return False
                result = self._driver.write(tag, value)
                if result.error:
                    logger.error(f"Error writing {tag}: {result.error}")
                    return False
                return True
            except Exception as e:
                logger.error(f"Exception writing {tag}: {e}")
                self._connected = False
                return False

    def _ensure_connected_unlocked(self) -> bool:
        """
        Ensure PLC connection is active, reconnect if needed.
        Must be called with lock already held.
        """
        if self._connected and self._driver:
            return True

        # Try to connect
        try:
            self._driver = LogixDriver(self.ip, slot=self.slot)
            self._driver.open()
            self._connected = True
            logger.info(f"Reconnected to PLC at {self.ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to PLC: {e}")
            self._connected = False
            return False
