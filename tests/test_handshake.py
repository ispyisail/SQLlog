"""Tests for handshake state machine."""

import pytest
from unittest.mock import Mock, MagicMock

from src.core.handshake import (
    HandshakeStateMachine,
    HandshakeState,
    ErrorCode,
    ConnectionStatus
)


class TestHandshakeStateMachine:
    """Tests for HandshakeStateMachine class."""

    @pytest.fixture
    def mock_plc(self):
        """Create mock PLC client."""
        plc = Mock()
        plc.is_connected = True
        plc.read_trigger.return_value = 0
        plc.write_trigger.return_value = True
        plc.read_all_recipe_data.return_value = {"RECIPE_NUMBER": 1, "TOTAL_WT": 1000}
        plc.write_error_code.return_value = True
        return plc

    @pytest.fixture
    def mock_sql(self):
        """Create mock SQL client."""
        sql = Mock()
        sql.is_connected = True
        sql.insert_record.return_value = True
        return sql

    @pytest.fixture
    def mock_cache(self):
        """Create mock local cache."""
        cache = Mock()
        cache.add_record.return_value = True
        return cache

    @pytest.fixture
    def state_machine(self, mock_plc, mock_sql, mock_cache):
        """Create state machine with mocks."""
        return HandshakeStateMachine(
            plc=mock_plc,
            sql=mock_sql,
            cache=mock_cache,
            mappings={"RECIPE_NUMBER": "Recipe_Number"},
            validation={}
        )

    def test_initial_state_is_idle(self, state_machine):
        """State machine should start in IDLE state."""
        assert state_machine.current_state == HandshakeState.IDLE

    def test_poll_in_idle_no_trigger(self, state_machine, mock_plc):
        """Polling in IDLE with no trigger should stay in IDLE."""
        mock_plc.read_trigger.return_value = 0

        state_machine.poll()

        assert state_machine.current_state == HandshakeState.IDLE
        mock_plc.read_all_recipe_data.assert_not_called()

    def test_poll_detects_trigger(self, state_machine, mock_plc, mock_sql):
        """Polling should detect trigger and process handshake."""
        mock_plc.read_trigger.return_value = 1

        state_machine.poll()

        # Should have read recipe and completed handshake
        mock_plc.read_all_recipe_data.assert_called_once()
        mock_sql.insert_record.assert_called_once()
        assert state_machine.current_state == HandshakeState.IDLE

    def test_successful_handshake_sequence(self, state_machine, mock_plc, mock_sql):
        """Complete handshake should write acknowledge then idle."""
        mock_plc.read_trigger.return_value = 1

        state_machine.poll()

        # Should have written 2 (acknowledge) then 0 (idle)
        calls = mock_plc.write_trigger.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == HandshakeState.ACKNOWLEDGE
        assert calls[1][0][0] == HandshakeState.IDLE

    def test_sql_failure_uses_cache(self, state_machine, mock_plc, mock_sql, mock_cache):
        """SQL failure should fall back to local cache."""
        mock_plc.read_trigger.return_value = 1
        mock_sql.insert_record.return_value = False

        state_machine.poll()

        # Should have tried cache
        mock_cache.add_record.assert_called_once()
        # Should still complete handshake
        assert state_machine.current_state == HandshakeState.IDLE

    def test_plc_read_failure_sets_fault(self, state_machine, mock_plc):
        """PLC read failure should set fault state."""
        mock_plc.read_trigger.return_value = 1
        mock_plc.read_all_recipe_data.return_value = None

        state_machine.poll()

        assert state_machine.current_state == HandshakeState.FAULT
        assert state_machine.last_error == ErrorCode.PLC_READ_FAILED
        mock_plc.write_trigger.assert_called_with(HandshakeState.FAULT)

    def test_validation_failure_sets_fault(self, state_machine, mock_plc):
        """Validation failure should set fault state."""
        mock_plc.read_trigger.return_value = 1
        mock_plc.read_all_recipe_data.return_value = {"TOTAL_WT": -100}

        # Add validation rules
        state_machine.validation = {
            "limits": {"TOTAL_WT": {"min": 0, "max": 50000}}
        }

        state_machine.poll()

        assert state_machine.current_state == HandshakeState.FAULT
        assert state_machine.last_error == ErrorCode.VALIDATION_FAILED

    def test_fault_recovery_on_plc_reset(self, state_machine, mock_plc):
        """Fault state should recover when PLC resets trigger to 0."""
        # Put into fault state
        state_machine._current_state = HandshakeState.FAULT
        state_machine._last_error = ErrorCode.PLC_READ_FAILED

        # PLC resets trigger to 0
        mock_plc.read_trigger.return_value = 0

        state_machine.poll()

        # Should recover to IDLE
        assert state_machine.current_state == HandshakeState.IDLE
        assert state_machine.last_error == ErrorCode.NONE
        mock_plc.write_error_code.assert_called_with(ErrorCode.NONE)

    def test_fault_stays_until_acknowledged(self, state_machine, mock_plc):
        """Fault state should persist if PLC hasn't reset."""
        state_machine._current_state = HandshakeState.FAULT
        state_machine._last_error = ErrorCode.PLC_READ_FAILED

        # PLC still shows fault (99)
        mock_plc.read_trigger.return_value = 99

        state_machine.poll()

        # Should stay in fault
        assert state_machine.current_state == HandshakeState.FAULT

    def test_get_status_connected(self, state_machine, mock_plc, mock_sql):
        """Status should be connected when all OK."""
        mock_plc.is_connected = True

        status = state_machine.get_status()

        assert status == ConnectionStatus.CONNECTED

    def test_get_status_plc_offline(self, state_machine, mock_plc):
        """Status should be plc_offline when PLC disconnected."""
        mock_plc.is_connected = False

        status = state_machine.get_status()

        assert status == ConnectionStatus.PLC_OFFLINE

    def test_get_status_fault(self, state_machine):
        """Status should be fault when in fault state."""
        state_machine._current_state = HandshakeState.FAULT

        status = state_machine.get_status()

        assert status == ConnectionStatus.FAULT

    def test_force_clear_fault(self, state_machine, mock_plc):
        """force_clear_fault should manually reset from fault."""
        state_machine._current_state = HandshakeState.FAULT
        state_machine._last_error = ErrorCode.PLC_READ_FAILED

        state_machine.force_clear_fault()

        assert state_machine.current_state == HandshakeState.IDLE
        assert state_machine.last_error == ErrorCode.NONE
        mock_plc.write_error_code.assert_called_with(ErrorCode.NONE)
        mock_plc.write_trigger.assert_called_with(HandshakeState.IDLE)
