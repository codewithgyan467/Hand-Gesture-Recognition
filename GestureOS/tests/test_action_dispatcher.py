"""Unit tests for ActionDispatcher, safety gating, and rate limiting."""

import pytest
from app.core.types import ActionIntent, IntentType, GestureState
from app.core.state_machine import GestureStateMachine
from app.actions.dispatcher import ActionDispatcher
from app.platform.mock_controller import MockOSController
from app.actions.cooldown import ActionCooldownManager
from app.core.config import CooldownConfig


def test_dispatcher_blocked_when_inactive():
    mock_os = MockOSController()
    fsm = GestureStateMachine()
    dispatcher = ActionDispatcher(mock_os, fsm)

    intent = ActionIntent(intent_type=IntentType.LEFT_CLICK)
    dispatched = dispatcher.dispatch(intent)

    # Must be blocked because fsm is INACTIVE
    assert not dispatched
    assert len(mock_os.action_history) == 0


def test_dispatcher_executes_when_active():
    mock_os = MockOSController()
    fsm = GestureStateMachine()
    fsm.transition_to(GestureState.ACTIVE)
    dispatcher = ActionDispatcher(mock_os, fsm)

    intent = ActionIntent(intent_type=IntentType.LEFT_CLICK)
    dispatched = dispatcher.dispatch(intent)

    assert dispatched
    assert len(mock_os.action_history) == 1
    assert mock_os.action_history[0]["action"] == "left_click"


def test_dispatcher_enforces_click_cooldown():
    mock_os = MockOSController()
    fsm = GestureStateMachine()
    fsm.transition_to(GestureState.ACTIVE)
    cd_mgr = ActionCooldownManager(CooldownConfig(left_click_ms=250))
    dispatcher = ActionDispatcher(mock_os, fsm, cooldown_manager=cd_mgr)

    intent = ActionIntent(intent_type=IntentType.LEFT_CLICK)

    # First click allowed at t=1.0
    cd_mgr.is_action_allowed(IntentType.LEFT_CLICK, timestamp=1.0)
    dispatcher.dispatch(intent)
    assert len(mock_os.action_history) == 1

    # Second click at t=1.1 (100ms later, < 250ms) -> BLOCKED
    dispatched2 = dispatcher.dispatch(intent)
    assert not dispatched2
    assert len(mock_os.action_history) == 1


def test_dispatcher_volume_rate_limiting():
    mock_os = MockOSController()
    fsm = GestureStateMachine()
    fsm.transition_to(GestureState.ACTIVE)
    dispatcher = ActionDispatcher(mock_os, fsm)

    # Dispatch volume set
    intent1 = ActionIntent(intent_type=IntentType.VOLUME_SET, params={"level": 70.0})
    ok1 = dispatcher.dispatch(intent1)
    assert ok1
    assert mock_os.get_volume() == 70.0

    # Rapid immediate duplicate (< 1/15s) -> throttled
    intent2 = ActionIntent(intent_type=IntentType.VOLUME_SET, params={"level": 72.0})
    ok2 = dispatcher.dispatch(intent2)
    assert not ok2
