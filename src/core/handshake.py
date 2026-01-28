"""
Handshake State Machine - Bulletproof 4-state PLC handshake
"""

import time
from enum import IntEnum
from typing import Callable
from loguru import logger

from .plc_client import PLCClient
from .sql_client import SQLClient
from .local_cache import LocalCache
from ..utils.validators import validate_recipe_data


class HandshakeState(IntEnum):
    """Handshake states for PLC communication."""
    IDLE = 0
    TRIGGERED = 1
    ACKNOWLEDGE = 2
    FAULT = 99


class ErrorCode(IntEnum):
    """Error codes written to PLC on fault."""
    NONE = 0
    PLC_READ_FAILED = 1
    VALIDATION_FAILED = 2
    SQL_AND_CACHE_FAILED = 3
    PLC_WRITE_FAILED = 4


class ConnectionStatus:
    """Connection status for tray app."""
    CONNECTED = "connected"          # PLC + SQL OK
    SQL_OFFLINE = "sql_offline"      # PLC OK, SQL down (caching)
    PLC_OFFLINE = "plc_offline"      # PLC down
    FAULT = "fault"                  # In fault state


class HandshakeStateMachine:
    """
    Implements the bulletproof 4-state handshake:

    State 0 (Idle): Wait for Recipe_Trigger == 1
    State 1 (Triggered): PLC requests logging
    State 2 (Acknowledge): Python reads UDT, writes 2 to PLC
    State 0 (Complete): SQL commit successful, reset to 0
    State 99 (Fault): Error occurred, error code written

    Fault Recovery:
    - When in FAULT state, monitors for PLC to reset trigger to 0
    - Once PLC acknowledges fault (resets to 0), clears error and returns to IDLE
    """

    def __init__(
        self,
        plc: PLCClient,
        sql: SQLClient,
        cache: LocalCache,
        mappings: dict,
        validation: dict,
        extra_mappings: dict = None,
        logger=logger,
        status_callback: Callable[[str], None] = None
    ):
        self.plc = plc
        self.sql = sql
        self.cache = cache
        self.mappings = mappings
        self.extra_mappings = extra_mappings or {}
        self.validation = validation
        self.logger = logger
        self.status_callback = status_callback

        self._current_state = HandshakeState.IDLE
        self._last_error = ErrorCode.NONE
        self._fault_time = None
        self._sql_was_down = False

    @property
    def current_state(self) -> HandshakeState:
        return self._current_state

    @property
    def last_error(self) -> ErrorCode:
        return self._last_error

    def get_status(self) -> str:
        """Get current connection status for tray app."""
        if self._current_state == HandshakeState.FAULT:
            return ConnectionStatus.FAULT
        if not self.plc.is_connected:
            return ConnectionStatus.PLC_OFFLINE
        if self._sql_was_down:
            return ConnectionStatus.SQL_OFFLINE
        return ConnectionStatus.CONNECTED

    def _update_status(self):
        """Notify status callback of state change."""
        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")

    def poll(self):
        """Poll the PLC and process state machine."""
        trigger = self.plc.read_trigger()

        if trigger is None:
            # PLC communication error
            self._update_status()
            return

        # Handle based on current state
        if self._current_state == HandshakeState.IDLE:
            if trigger == HandshakeState.TRIGGERED:
                self._handle_trigger()

        elif self._current_state == HandshakeState.FAULT:
            # Fault recovery: wait for PLC to reset trigger to 0
            self._handle_fault_recovery(trigger)

        self._update_status()

    def _handle_trigger(self):
        """Handle a new trigger from PLC."""
        self.logger.info("Trigger detected, reading recipe data")
        self._sql_was_down = False

        # Step 1: Read recipe data (including extra tags)
        recipe_data = self.plc.read_all_recipe_data()
        if recipe_data is None:
            self._set_fault(ErrorCode.PLC_READ_FAILED)
            return

        # Step 2: Acknowledge by writing 2
        if not self.plc.write_trigger(HandshakeState.ACKNOWLEDGE):
            self._set_fault(ErrorCode.PLC_WRITE_FAILED)
            return

        self._current_state = HandshakeState.ACKNOWLEDGE
        self.logger.info("Acknowledged trigger, validating data")

        # Step 3: Validate data
        is_valid, errors = validate_recipe_data(recipe_data, self.validation)
        if not is_valid:
            self.logger.error(f"Validation failed: {errors}")
            self._set_fault(ErrorCode.VALIDATION_FAILED)
            return

        # Step 4: Attempt SQL insert
        # Merge extra mappings into mappings
        all_mappings = {**self.mappings, **self.extra_mappings}

        if self.sql.insert_record(recipe_data, all_mappings):
            self.logger.info("Record inserted to SQL Server")
        else:
            # SQL failed, try local cache
            self.logger.warning("SQL insert failed, caching locally")
            self._sql_was_down = True
            if not self.cache.add_record(recipe_data, all_mappings):
                self._set_fault(ErrorCode.SQL_AND_CACHE_FAILED)
                return

        # Step 5: Complete handshake
        if not self.plc.write_trigger(HandshakeState.IDLE):
            self.logger.error("Failed to reset trigger to 0")
            # Don't fault here - data is already saved

        self._current_state = HandshakeState.IDLE
        self.logger.info("Handshake complete")

    def _handle_fault_recovery(self, trigger: int):
        """
        Handle fault state recovery.

        Waits for PLC to acknowledge fault by resetting trigger to 0.
        This ensures the PLC operator has seen the fault before continuing.
        """
        if trigger == HandshakeState.IDLE:
            # PLC has acknowledged the fault and reset
            self.logger.info(f"Fault acknowledged by PLC, recovering from {self._last_error.name}")

            # Clear error code on PLC
            self.plc.write_error_code(ErrorCode.NONE)

            # Return to idle state
            self._current_state = HandshakeState.IDLE
            self._last_error = ErrorCode.NONE
            self._fault_time = None

            self.logger.info("Fault recovery complete, returning to IDLE")

    def _set_fault(self, error_code: ErrorCode):
        """Set fault state and write error code to PLC."""
        self.logger.error(f"Fault: {error_code.name} ({error_code.value})")

        self._last_error = error_code
        self._fault_time = time.time()

        self.plc.write_error_code(error_code.value)
        self.plc.write_trigger(HandshakeState.FAULT)

        self._current_state = HandshakeState.FAULT
        self._update_status()

    def force_clear_fault(self):
        """
        Force clear fault state (for manual intervention).
        Use with caution - should normally let PLC acknowledge.
        """
        if self._current_state == HandshakeState.FAULT:
            self.logger.warning("Force clearing fault state")
            self.plc.write_error_code(ErrorCode.NONE)
            self.plc.write_trigger(HandshakeState.IDLE)
            self._current_state = HandshakeState.IDLE
            self._last_error = ErrorCode.NONE
            self._fault_time = None
            self._update_status()
