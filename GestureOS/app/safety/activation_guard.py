"""Activation guard ensuring GestureOS operates in passive mode until deliberate activation hold."""

from __future__ import annotations
import time
from typing import Optional
from app.core.types import GestureType, GestureRecognitionResult
from app.core.state_machine import GestureStateMachine
from app.diagnostics.logger import get_logger

logger = get_logger("activation_guard")


class ActivationGuard:
    """Guards against unintentional computer control. Defaults to user-controlled passive mode."""

    def __init__(
        self,
        state_machine: GestureStateMachine,
        activation_hold_sec: float = 1.0,
        allow_gesture_activation: bool = False,
    ) -> None:
        self.state_machine = state_machine
        self.activation_hold_sec = activation_hold_sec
        self.allow_gesture_activation = allow_gesture_activation

    def evaluate(self, result: GestureRecognitionResult) -> bool:
        """Processes current frame gesture through activation state machine.
        
        Returns True if system is armed and active for OS action generation.
        """
        # If in Emergency Stop, no actions can pass
        if self.state_machine.is_emergency_stopped:
            return False

        if not self.state_machine.is_active:
            # Only update gesture activation if user enabled it in config
            if self.allow_gesture_activation:
                is_open_palm = (result.gesture == GestureType.OPEN_PALM and result.confidence >= 0.85)
                activated = self.state_machine.update_activation(is_open_palm, self.activation_hold_sec)
                if activated:
                    logger.info("GestureOS ACTIVATED via sustained Open Palm hold.")
            return False

        # If already active, check for pause (Fist)
        if result.gesture == GestureType.FIST and result.confidence >= 0.90:
            # Temporary pause
            return False

        return True
