"""Unit tests for PinchEngine, hysteresis, drag transitions, and double-clicks."""

import pytest
from app.gestures.pinch_engine import PinchEngine, PinchState, PinchEvent
from app.core.config import PinchConfig


def test_pinch_hysteresis_and_click():
    cfg = PinchConfig(pinch_threshold=0.28, release_threshold=0.36, cooldown_ms=100)
    engine = PinchEngine(cfg)

    # 1. Wide open (dist = 0.8) -> IDLE
    ev = engine.update(0.8, timestamp=1.0)
    assert ev == PinchEvent.NONE
    assert not engine.is_pinched

    # 2. Closes to 0.25 (below threshold 0.28) -> PINCH_ENGAGED
    ev = engine.update(0.25, timestamp=1.05)
    assert ev == PinchEvent.NONE
    assert engine.is_pinched

    # 3. Flutters to 0.32 (above 0.28 but below release threshold 0.36) -> Remains pinched!
    ev = engine.update(0.32, timestamp=1.10)
    assert ev == PinchEvent.NONE
    assert engine.is_pinched

    # 4. Opens to 0.40 (above release threshold 0.36 within 150ms) -> CLICK!
    ev = engine.update(0.40, timestamp=1.20)
    assert ev == PinchEvent.CLICK
    assert not engine.is_pinched


def test_pinch_hold_to_drag():
    cfg = PinchConfig(pinch_threshold=0.28, release_threshold=0.36, pinch_hold_time_sec=0.30)
    engine = PinchEngine(cfg)

    # Pinch down at t=1.0
    engine.update(0.20, timestamp=1.0)
    assert engine.is_pinched

    # Hold at t=1.2 (200ms held, < 300ms)
    ev = engine.update(0.20, timestamp=1.2)
    assert ev == PinchEvent.NONE

    # Hold past 300ms at t=1.35 -> DRAG_START
    ev = engine.update(0.20, timestamp=1.35)
    assert ev == PinchEvent.DRAG_START
    assert engine.is_dragging

    # Continue moving while pinched -> DRAG_MOVE
    ev = engine.update(0.22, timestamp=1.40)
    assert ev == PinchEvent.DRAG_MOVE

    # Release fingers -> DRAG_END
    ev = engine.update(0.45, timestamp=1.50)
    assert ev == PinchEvent.DRAG_END
    assert not engine.is_pinched
