"""Action-specific cooldown, rate-limiting, and debouncing manager."""

from __future__ import annotations
import time
from typing import Dict
from app.core.types import IntentType
from app.core.config import CooldownConfig


class ActionCooldownManager:
    """Enforces non-blocking cooldown intervals per intent type to prevent repeat spam."""

    def __init__(self, config: Optional[CooldownConfig] = None) -> None:
        self.config = config or CooldownConfig()
        self._last_execution_times: Dict[IntentType, float] = {}

    def is_action_allowed(self, intent_type: IntentType, timestamp: Optional[float] = None) -> bool:
        if timestamp is None:
            timestamp = time.time()

        # Mouse movement and drag movements are continuous streams and not rate-blocked here
        if intent_type in (IntentType.MOUSE_MOVE, IntentType.DRAG_MOVE):
            return True

        last_time = self._last_execution_times.get(intent_type, 0.0)
        cooldown_sec = self._get_cooldown_duration(intent_type)

        if (timestamp - last_time) >= cooldown_sec:
            return True
        return False

    def mark_executed(self, intent_type: IntentType, timestamp: Optional[float] = None) -> None:
        if timestamp is None:
            timestamp = time.time()
        self._last_execution_times[intent_type] = timestamp

    def _get_cooldown_duration(self, intent_type: IntentType) -> float:
        if intent_type == IntentType.LEFT_CLICK:
            return self.config.left_click_ms / 1000.0
        elif intent_type == IntentType.RIGHT_CLICK:
            return self.config.right_click_ms / 1000.0
        elif intent_type == IntentType.DOUBLE_CLICK:
            return self.config.double_click_ms / 1000.0
        elif intent_type in (IntentType.SCROLL_VERTICAL, IntentType.SCROLL_HORIZONTAL):
            return self.config.scroll_ms / 1000.0
        elif intent_type in (
            IntentType.BROWSER_BACK, IntentType.BROWSER_FORWARD,
            IntentType.WINDOW_NEXT, IntentType.WINDOW_PREV,
            IntentType.PRESENTATION_NEXT, IntentType.PRESENTATION_PREV,
            IntentType.MEDIA_NEXT, IntentType.MEDIA_PREV
        ):
            return self.config.swipe_ms / 1000.0
        elif intent_type == IntentType.MODE_SWITCH:
            return self.config.mode_switch_ms / 1000.0

        return 0.25 # Default 250ms fallback

    def reset(self) -> None:
        self._last_execution_times.clear()
