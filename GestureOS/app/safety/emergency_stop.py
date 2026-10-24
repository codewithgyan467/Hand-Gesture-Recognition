"""Emergency Stop guard monitoring global ESC key, dual-fist gestures, and manual UI triggers."""

from __future__ import annotations
import threading
from typing import Optional, Callable, Any
from pynput import keyboard
from app.core.state_machine import GestureStateMachine
from app.diagnostics.logger import get_logger

logger = get_logger("emergency_stop")


class EmergencyStopGuard:
    """Monitors global safety kill-switches (ESC key, dual fists, UI button) to instantly lock GestureOS."""

    def __init__(self, state_machine: GestureStateMachine, safety_controller: Optional[Any] = None) -> None:
        self.state_machine = state_machine
        self.safety_controller = safety_controller
        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False

    def start_keyboard_listener(self) -> None:
        if self._listener is not None:
            return

        last_esc_time = [0.0]

        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    import time
                    now = time.time()
                    if now - last_esc_time[0] < 0.4:
                        return
                    last_esc_time[0] = now

                    if self.state_machine.is_emergency_stopped:
                        logger.info("Global ESC key pressed: Clearing Emergency Stop and re-arming Touchless Control.")
                        self.reset()
                    else:
                        logger.warning("Global ESC key pressed: Engaging Emergency Safety Stop.")
                        self.trigger("Global ESC key pressed")
            except Exception as e:
                logger.error(f"Error in emergency keyboard hook: {e}")

        try:
            self._listener = keyboard.Listener(on_press=on_press)
            self._listener.daemon = True
            self._listener.start()
            self._is_running = True
            logger.info("Global emergency stop ESC keyboard listener started.")
        except Exception as e:
            logger.warning(f"Could not hook keyboard listener: {e}")

    def stop_keyboard_listener(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self._is_running = False

    def trigger(self, reason: str = "Manual emergency stop") -> None:
        logger.warning(f"Emergency stop triggered: {reason}")
        if self.safety_controller is not None:
            self.safety_controller.trigger_emergency_stop(reason)
        else:
            self.state_machine.trigger_emergency_stop(reason)

    def reset(self) -> None:
        logger.info("Emergency stop cleared by user.")
        if self.safety_controller is not None:
            self.safety_controller.clear_emergency_stop(activate=True)
        else:
            self.state_machine.clear_emergency_stop(activate=True)
