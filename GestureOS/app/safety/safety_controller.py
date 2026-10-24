"""Central Safety Controller ensuring fail-safe execution and emergency stop guarantees."""

from __future__ import annotations
import threading
from typing import Optional, List, Callable
from app.platform.base_controller import BaseOSController
from app.core.state_machine import GestureStateMachine
from app.core.events import EventBus, EventType, default_event_bus
from app.diagnostics.logger import get_logger

logger = get_logger("safety_controller")


class SafetyController:
    """Central safety governor managing emergency stop, fail-safe key/mouse releases, and exception locks."""

    def __init__(
        self,
        state_machine: GestureStateMachine,
        controller: BaseOSController,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.state_machine = state_machine
        self.controller = controller
        self.event_bus = event_bus or default_event_bus
        self._lock = threading.Lock()
        self._held_keys: List[str] = []
        self._is_dragging: bool = False

    @property
    def is_emergency_stopped(self) -> bool:
        return self.state_machine.is_emergency_stopped

    def trigger_emergency_stop(self, reason: str = "Emergency stop triggered") -> None:
        """Immediately halts all automation, releases held mouse buttons/keys, and enters lock state."""
        with self._lock:
            logger.critical(f"EMERGENCY SAFETY LOCK ENGAGED: {reason}")
            # 1. Transition state machine to emergency stop
            self.state_machine.trigger_emergency_stop(reason)

            # 2. Release physical mouse buttons to prevent sticky drags
            try:
                self.controller.mouse_up("left")
                self.controller.mouse_up("right")
            except Exception as e:
                logger.error(f"Error releasing mouse buttons on emergency stop: {e}")

            # 3. Release any recorded held keyboard keys
            for k in list(self._held_keys):
                try:
                    self.controller.press_key(k)
                except Exception:
                    pass
            self._held_keys.clear()
            self._is_dragging = False

            # 4. Notify event bus
            self.event_bus.publish(EventType.EMERGENCY_STOP_TRIGGERED, {
                "reason": reason,
            })

    def release_all_inputs(self) -> None:
        """Physically releases any held mouse buttons or keys immediately."""
        with self._lock:
            try:
                self.controller.mouse_up("left")
                self.controller.mouse_up("right")
            except Exception as e:
                logger.debug(f"Error releasing mouse buttons: {e}")
            self._held_keys.clear()
            self._is_dragging = False

    def clear_emergency_stop(self, activate: bool = True) -> None:
        """Clears the emergency lock state and optionally re-arms Touchless Mouse control."""
        with self._lock:
            logger.info("Emergency safety lock cleared by user.")
            self.state_machine.clear_emergency_stop(activate=activate)
            self.event_bus.publish(EventType.EMERGENCY_STOP_CLEARED, {
                "active": activate,
            })

    def notify_drag_start(self) -> None:
        self._is_dragging = True

    def notify_drag_end(self) -> None:
        self._is_dragging = False

    def handle_camera_failure(self, camera_index: int = 0) -> None:
        """Safely neutralizes any active drag or OS manipulation when camera feed is lost."""
        with self._lock:
            logger.warning(f"Camera feed lost on index {camera_index}. Neutralizing OS control to fail-safe.")
            if self._is_dragging:
                try:
                    self.controller.mouse_up("left")
                except Exception:
                    pass
                self._is_dragging = False

    def handle_critical_exception(self, e: Exception, component: str = "Unknown") -> None:
        """Handles unexpected runtime exceptions by locking into a safe state."""
        logger.critical(f"Critical exception in {component}: {e}. Triggering fail-safe emergency stop.", exc_info=True)
        self.trigger_emergency_stop(f"Critical failure in {component}: {str(e)}")
