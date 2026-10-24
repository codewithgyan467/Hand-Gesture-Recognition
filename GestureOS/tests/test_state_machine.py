"""Unit tests for GestureStateMachine and ActivationGuard."""

import pytest
from app.core.state_machine import GestureStateMachine
from app.core.types import GestureState
from app.safety.activation_guard import ActivationGuard
from app.core.types import GestureRecognitionResult, GestureType


def test_state_machine_initial_state():
    fsm = GestureStateMachine()
    assert fsm.current_state == GestureState.INACTIVE
    assert not fsm.is_active


def test_activation_hold_progress():
    fsm = GestureStateMachine()
    # 0.5s into 1.0s hold
    fsm._activation_start_time = 1.0
    # Hold not done at t=1.5
    done = fsm.update_activation(is_holding_activation_gesture=True, required_hold_sec=1.0, timestamp=1.5)
    assert not done
    assert fsm.current_state == GestureState.ACTIVATING

    # Release early at t=1.6 -> returns to INACTIVE
    fsm.update_activation(is_holding_activation_gesture=False, timestamp=1.6)
    assert fsm.current_state == GestureState.INACTIVE


def test_emergency_stop_hard_lock():
    fsm = GestureStateMachine()
    fsm.transition_to(GestureState.ACTIVE)
    assert fsm.is_active

    # Trigger emergency stop
    fsm.trigger_emergency_stop("Safety test")
    assert fsm.is_emergency_stopped

    # Trying to transition to ACTIVE while emergency stopped must FAIL
    ok = fsm.transition_to(GestureState.ACTIVE)
    assert not ok
    assert fsm.is_emergency_stopped

    # Clear emergency stop explicitly
    fsm.clear_emergency_stop()
    assert not fsm.is_emergency_stopped
    assert fsm.current_state == GestureState.INACTIVE
