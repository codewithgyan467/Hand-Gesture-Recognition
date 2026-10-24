"""Scale-invariant Pinch Engine with movement-based drag intent, hysteresis, and click debouncing."""

from __future__ import annotations
import math
import time
from enum import Enum, auto
from typing import Optional, Tuple, Any
from app.core.config import PinchConfig


class PinchState(Enum):
    IDLE = auto()
    PINCH_ENGAGED = auto()
    PINCH_HOLD_DRAG = auto()


class PinchEvent(Enum):
    NONE = auto()
    CLICK = auto()
    DOUBLE_CLICK = auto()
    DRAG_START = auto()
    DRAG_MOVE = auto()
    DRAG_END = auto()


class PinchEngine:
    """Detects scale-invariant pinch gestures, distinguishing taps, double clicks, and drag-and-drop.
    
    Infers intent naturally from movement-based drag tracking, velocity, and hold duration.
    """

    def __init__(self, config: Optional[PinchConfig] = None) -> None:
        self.config = config or PinchConfig()
        self._state = PinchState.IDLE
        self._pinch_start_time: float = 0.0
        self._pinch_start_pos: Optional[Tuple[float, float]] = None
        self._last_click_time: float = 0.0
        self._last_event_time: float = 0.0
        # Movement threshold to declare a drag (in normalized units or pixels)
        self.movement_drag_threshold: float = 0.024
        self._has_moved_significantly: bool = False

    @property
    def is_pinched(self) -> bool:
        return self._state in (PinchState.PINCH_ENGAGED, PinchState.PINCH_HOLD_DRAG)

    @property
    def is_dragging(self) -> bool:
        return self._state == PinchState.PINCH_HOLD_DRAG

    def update(
        self,
        normalized_dist: float,
        timestamp: Optional[float] = None,
        cursor_pos: Optional[Any] = None,
    ) -> PinchEvent:
        """Processes normalized thumb-to-finger distance & movement and returns recognized PinchEvent."""
        if timestamp is None:
            timestamp = time.time()

        pos_tuple: Optional[Tuple[float, float]] = None
        if cursor_pos is not None:
            if hasattr(cursor_pos, "x") and hasattr(cursor_pos, "y"):
                pos_tuple = (float(cursor_pos.x), float(cursor_pos.y))
            elif isinstance(cursor_pos, (tuple, list)) and len(cursor_pos) >= 2:
                pos_tuple = (float(cursor_pos[0]), float(cursor_pos[1]))

        event = PinchEvent.NONE

        if self._state == PinchState.IDLE:
            # Check for initial pinch threshold entry
            if normalized_dist <= self.config.pinch_threshold:
                self._state = PinchState.PINCH_ENGAGED
                self._pinch_start_time = timestamp
                self._pinch_start_pos = pos_tuple
                self._has_moved_significantly = False

        elif self._state == PinchState.PINCH_ENGAGED:
            # Check movement distance if position is available
            if pos_tuple is not None and self._pinch_start_pos is not None:
                dx = pos_tuple[0] - self._pinch_start_pos[0]
                dy = pos_tuple[1] - self._pinch_start_pos[1]
                dist_moved = math.hypot(dx, dy)
                # If coordinates are pixels (> 1.0), adjust threshold to pixel scale
                threshold = 24.0 if (self._pinch_start_pos[0] > 1.0) else self.movement_drag_threshold
                if dist_moved >= threshold:
                    self._has_moved_significantly = True
                    self._state = PinchState.PINCH_HOLD_DRAG
                    return PinchEvent.DRAG_START

            # Hysteresis check: has user opened fingers past release threshold?
            if normalized_dist >= self.config.release_threshold:
                # Finger released quickly without dragging -> Click or Double Click
                self._state = PinchState.IDLE
                self._pinch_start_pos = None

                # Enforce minimum cooldown between click events
                cooldown_sec = self.config.cooldown_ms / 1000.0
                if (timestamp - self._last_event_time) >= cooldown_sec:
                    # Check for double-click
                    if (timestamp - self._last_click_time) <= self.config.double_click_window_sec:
                        event = PinchEvent.DOUBLE_CLICK
                        self._last_click_time = 0.0
                    else:
                        event = PinchEvent.CLICK
                        self._last_click_time = timestamp

                    self._last_event_time = timestamp
            else:
                # Still pinching: check if held long enough to become a Drag even without movement
                held_duration = timestamp - self._pinch_start_time
                if held_duration >= self.config.pinch_hold_time_sec:
                    self._state = PinchState.PINCH_HOLD_DRAG
                    event = PinchEvent.DRAG_START

        elif self._state == PinchState.PINCH_HOLD_DRAG:
            # Currently dragging: continue or end
            if normalized_dist >= self.config.release_threshold:
                self._state = PinchState.IDLE
                self._pinch_start_pos = None
                self._has_moved_significantly = False
                event = PinchEvent.DRAG_END
            else:
                event = PinchEvent.DRAG_MOVE

        return event

    def cancel_drag(self) -> Optional[PinchEvent]:
        """Safely ends active drag when hand is lost or engine stopped."""
        if self._state == PinchState.PINCH_HOLD_DRAG:
            self.reset()
            return PinchEvent.DRAG_END
        self.reset()
        return None

    def reset(self) -> None:
        self._state = PinchState.IDLE
        self._pinch_start_time = 0.0
        self._pinch_start_pos = None
        self._has_moved_significantly = False
