"""Tests for Platform Abstraction, SafetyController fail-safe emergency stop, and Safe Mode."""

import pytest
from app.platform.capabilities import PlatformCapabilities, detect_platform_capabilities
from app.platform.factory import get_platform_controller
from app.platform.mock_controller import MockOSController
from app.safety.safety_controller import SafetyController
from app.core.state_machine import GestureStateMachine
from app.actions.dispatcher import ActionDispatcher
from app.core.types import ActionIntent, IntentType, GestureState


def test_platform_capabilities_detection():
    caps = PlatformCapabilities.detect()
    assert caps.os_name in ("win32", "darwin", "linux")
    assert caps.architecture != ""
    assert isinstance(caps.to_dict(), dict)
    assert caps.system in ("windows", "macos", "linux")


def test_platform_controller_factory():
    # Simulation / mock controller
    ctrl = get_platform_controller(use_mock=True, screen_width=1920, screen_height=1080)
    assert isinstance(ctrl, MockOSController)
    assert ctrl.get_screen_size() == (1920, 1080)


def test_safety_controller_releases_inputs_on_emergency_stop():
    ctrl = MockOSController()
    state_machine = GestureStateMachine()
    safety = SafetyController(controller=ctrl, state_machine=state_machine)

    # Simulate mouse button held down during drag
    ctrl.mouse_down("left")
    assert ctrl.is_left_down

    # Trigger emergency stop
    safety.trigger_emergency_stop("Safety test emergency stop")

    # SafetyController MUST physically release mouse button
    assert not ctrl.is_left_down
    assert state_machine.is_emergency_stopped


def test_action_dispatcher_safe_mode():
    ctrl = MockOSController()
    state_machine = GestureStateMachine()
    state_machine.transition_to(GestureState.ACTIVE, "Test active")
    dispatcher = ActionDispatcher(ctrl, state_machine, safe_mode=True)

    # In safe mode, automation action should be suppressed
    intent = ActionIntent(
        intent_type=IntentType.LEFT_CLICK,
        confidence=0.99,
        timestamp=1.0,
    )
    executed = dispatcher.dispatch(intent)
    assert not executed
    assert ctrl.last_click is None
