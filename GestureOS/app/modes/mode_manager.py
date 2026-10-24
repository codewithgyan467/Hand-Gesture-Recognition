"""Mode Manager coordinating active interaction modes and touchless mode switching."""

from __future__ import annotations
import time
from typing import Dict, Optional, List
from app.core.types import (
    InteractionMode,
    GestureType,
    GestureRecognitionResult,
    HandLandmarks,
    HandFeatures,
    ActionIntent,
)
from app.modes.base_mode import BaseMode
from app.modes.mouse_mode import MouseMode
from app.modes.media_mode import MediaMode
from app.modes.browser_mode import BrowserMode
from app.modes.presentation_mode import PresentationMode
from app.modes.window_mode import WindowMode
from app.modes.drawing_mode import DrawingMode
from app.cursor.cursor_engine import CursorEngine
from app.core.config import PinchConfig
from app.core.events import EventBus, EventType, default_event_bus
from app.diagnostics.logger import get_logger

logger = get_logger("mode_manager")


class ModeManager:
    """Manages active mode lifecycle and touchless mode switching."""

    def __init__(
        self,
        cursor_engine: CursorEngine,
        pinch_config: Optional[PinchConfig] = None,
        default_mode: InteractionMode = InteractionMode.MOUSE,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.cursor_engine = cursor_engine
        self.event_bus = event_bus or default_event_bus

        # Initialize all mode modules
        self._modes: Dict[InteractionMode, BaseMode] = {
            InteractionMode.MOUSE: MouseMode(cursor_engine, pinch_config),
            InteractionMode.MEDIA: MediaMode(cursor_engine),
            InteractionMode.BROWSER: BrowserMode(cursor_engine),
            InteractionMode.PRESENTATION: PresentationMode(cursor_engine),
            InteractionMode.WINDOW: WindowMode(cursor_engine),
            InteractionMode.DRAWING: DrawingMode(cursor_engine),
        }

        self._active_mode_key: InteractionMode = default_mode
        self._active_mode: BaseMode = self._modes[default_mode]
        self._active_mode.on_enter()

        # Touchless mode switching tracker
        self._mode_switch_start_time: Optional[float] = None
        self._switch_cooldown_expiry: float = 0.0

    @property
    def current_mode_type(self) -> InteractionMode:
        return self._active_mode_key

    @property
    def current_mode_name(self) -> str:
        return self._active_mode_key.value

    @property
    def active_mode(self) -> BaseMode:
        return self._active_mode

    @property
    def current_mode(self) -> BaseMode:
        return self._active_mode

    def get_mode(self, mode: InteractionMode) -> Optional[BaseMode]:
        return self._modes.get(mode)

    def switch_to_mode(self, new_mode: InteractionMode) -> bool:
        if new_mode not in self._modes:
            logger.warning(f"Unknown mode: {new_mode}")
            return False

        if new_mode == self._active_mode_key:
            return True

        old_key = self._active_mode_key
        self._active_mode.on_exit()
        self._active_mode_key = new_mode
        self._active_mode = self._modes[new_mode]
        self._active_mode.on_enter()

        logger.info(f"Switched mode from {old_key.value} -> {new_mode.value}")
        self.event_bus.publish(EventType.MODE_CHANGED, {
            "old_mode": old_key.value,
            "new_mode": new_mode.value,
        })
        return True

    def cycle_next_mode(self) -> InteractionMode:
        mode_order = [
            InteractionMode.MOUSE,
            InteractionMode.MEDIA,
            InteractionMode.BROWSER,
            InteractionMode.PRESENTATION,
            InteractionMode.WINDOW,
            InteractionMode.DRAWING,
        ]
        curr_idx = mode_order.index(self._active_mode_key)
        next_mode = mode_order[(curr_idx + 1) % len(mode_order)]
        self.switch_to_mode(next_mode)
        return next_mode

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
        secondary_result: Optional[GestureRecognitionResult] = None,
        secondary_landmarks: Optional[HandLandmarks] = None,
    ) -> Optional[ActionIntent]:
        # Check for touchless mode switching gesture (Peace gesture held for 1.2s)
        now = timestamp
        if gesture_result.gesture == GestureType.PEACE and gesture_result.confidence >= 0.88:
            if now > self._switch_cooldown_expiry:
                if self._mode_switch_start_time is None:
                    self._mode_switch_start_time = now
                elif now - self._mode_switch_start_time >= 1.2:
                    self.cycle_next_mode()
                    self._mode_switch_start_time = None
                    self._switch_cooldown_expiry = now + 1.5
                    return None
        else:
            self._mode_switch_start_time = None

        # Route to active mode implementation
        if self._active_mode_key == InteractionMode.MOUSE:
            return self._active_mode.process_gesture(
                gesture_result,
                landmarks,
                features,
                timestamp,
                secondary_result=secondary_result,
                secondary_landmarks=secondary_landmarks,
            )
        return self._active_mode.process_gesture(gesture_result, landmarks, features, timestamp)
