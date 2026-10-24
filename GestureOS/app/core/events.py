"""Thread-safe event system for decoupled cross-module communication in GestureOS."""

from __future__ import annotations
import threading
from typing import Callable, Dict, List, Any
from enum import Enum, auto


class EventType(str, Enum):
    FRAME_CAPTURED = "frame_captured"
    HAND_DETECTED = "hand_detected"
    TRACKING_LOST = "tracking_lost"
    GESTURE_RECOGNIZED = "gesture_recognized"
    INTENT_DISPATCHED = "intent_dispatched"
    STATE_CHANGED = "state_changed"
    MODE_CHANGED = "mode_changed"
    EMERGENCY_STOP_TRIGGERED = "emergency_stop_triggered"
    EMERGENCY_STOP_CLEARED = "emergency_stop_cleared"
    CAMERA_STATUS_CHANGED = "camera_status_changed"
    DIAGNOSTICS_UPDATED = "diagnostics_updated"
    CALIBRATION_STEP_ADVANCED = "calibration_step_advanced"


class EventBus:
    """Thread-safe publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)

    def publish(self, event_type: EventType, data: Any = None) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
        for cb in callbacks:
            try:
                cb(data)
            except Exception as e:
                # Never allow a single listener failure to crash event delivery
                pass


# Global singleton instance for easy cross-module access
default_event_bus = EventBus()
