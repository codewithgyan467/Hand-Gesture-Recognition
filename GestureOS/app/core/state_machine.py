"""Robust Finite State Machine governing GestureOS lifecycle and gesture safety transitions."""

from __future__ import annotations
import time
import threading
from typing import Optional, Callable
from app.core.types import GestureState, GestureType
from app.core.events import EventBus, EventType, default_event_bus


class GestureStateMachine:
    """Manages the operational states of GestureOS with explicit validation and callbacks."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._state: GestureState = GestureState.INACTIVE
        self._previous_state: GestureState = GestureState.INACTIVE
        self._lock = threading.RLock()
        self._event_bus = event_bus or default_event_bus
        self._activation_start_time: Optional[float] = None
        self._activation_progress: float = 0.0
        self._state_entered_time: float = time.time()
        self._current_gesture: GestureType = GestureType.NONE

    @property
    def current_state(self) -> GestureState:
        with self._lock:
            return self._state

    @property
    def previous_state(self) -> GestureState:
        with self._lock:
            return self._previous_state

    @property
    def time_in_current_state(self) -> float:
        with self._lock:
            return time.time() - self._state_entered_time

    @property
    def activation_progress(self) -> float:
        with self._lock:
            return self._activation_progress

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._state in (
                GestureState.ACTIVE,
                GestureState.GESTURE_DETECTED,
                GestureState.VALIDATING,
                GestureState.EXECUTING,
                GestureState.COOLDOWN,
                GestureState.TRACKING_LOST,
            )

    @property
    def is_emergency_stopped(self) -> bool:
        with self._lock:
            return self._state == GestureState.EMERGENCY_STOP

    def transition_to(self, new_state: GestureState, reason: str = "") -> bool:
        with self._lock:
            if self._state == new_state:
                return True

            # Emergency stop cannot be exited except by explicit clear_emergency_stop
            if self._state == GestureState.EMERGENCY_STOP and new_state != GestureState.INACTIVE:
                return False

            self._previous_state = self._state
            self._state = new_state
            self._state_entered_time = time.time()

            payload = {
                "old_state": self._previous_state.value,
                "new_state": self._state.value,
                "reason": reason,
                "timestamp": self._state_entered_time,
            }

        self._event_bus.publish(EventType.STATE_CHANGED, payload)
        return True

    def trigger_emergency_stop(self, reason: str = "Emergency stop triggered") -> None:
        with self._lock:
            self._previous_state = self._state
            self._state = GestureState.EMERGENCY_STOP
            self._state_entered_time = time.time()
            self._activation_progress = 0.0
            self._activation_start_time = None

        self._event_bus.publish(EventType.EMERGENCY_STOP_TRIGGERED, {"reason": reason})
        self._event_bus.publish(EventType.STATE_CHANGED, {
            "old_state": self._previous_state.value,
            "new_state": GestureState.EMERGENCY_STOP.value,
            "reason": reason,
            "timestamp": time.time(),
        })

    def clear_emergency_stop(self, activate: bool = False) -> None:
        with self._lock:
            if self._state == GestureState.EMERGENCY_STOP:
                self._previous_state = GestureState.EMERGENCY_STOP
                self._state = GestureState.ACTIVE if activate else GestureState.INACTIVE
                self._state_entered_time = time.time()
            new_st = self._state

        self._event_bus.publish(EventType.EMERGENCY_STOP_CLEARED, {})
        self._event_bus.publish(EventType.STATE_CHANGED, {
            "old_state": GestureState.EMERGENCY_STOP.value,
            "new_state": new_st.value,
            "reason": "Emergency stop cleared by user",
            "timestamp": time.time(),
        })

    def update_activation(
        self,
        is_holding_activation_gesture: bool,
        required_hold_sec: float = 1.0,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Updates activation progress. Returns True if activation just completed."""
        with self._lock:
            if self._state == GestureState.EMERGENCY_STOP:
                return False

            if self.is_active:
                # Already active
                return False

            now = timestamp if timestamp is not None else time.time()
            if is_holding_activation_gesture:
                if self._activation_start_time is None:
                    self._activation_start_time = now
                if self._state != GestureState.ACTIVATING:
                    self.transition_to(GestureState.ACTIVATING, "Activation gesture held")

                elapsed = now - self._activation_start_time
                self._activation_progress = min(1.0, elapsed / max(0.1, required_hold_sec))

                if self._activation_progress >= 1.0:
                    self._activation_start_time = None
                    self._activation_progress = 1.0
                    self.transition_to(GestureState.ACTIVE, "Activation completed successfully")
                    return True
            else:
                if self._activation_start_time is not None:
                    self._activation_start_time = None
                    self._activation_progress = 0.0
                    self.transition_to(GestureState.INACTIVE, "Activation gesture released early")

            return False

    def deactivate(self, reason: str = "User requested deactivation") -> None:
        with self._lock:
            if self._state != GestureState.EMERGENCY_STOP:
                self._activation_start_time = None
                self._activation_progress = 0.0
                self.transition_to(GestureState.INACTIVE, reason)
