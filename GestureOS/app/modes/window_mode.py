"""Desktop window management mode."""

from __future__ import annotations
from typing import Optional
from app.modes.base_mode import BaseMode
from app.core.types import (
    InteractionMode,
    GestureType,
    GestureRecognitionResult,
    HandLandmarks,
    HandFeatures,
    ActionIntent,
    IntentType,
)
from app.cursor.cursor_engine import CursorEngine


class WindowMode(BaseMode):
    """Window switcher and layout manager mode."""

    def __init__(self, cursor_engine: CursorEngine) -> None:
        super().__init__(InteractionMode.WINDOW, cursor_engine)

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # 1. Switch Active Application
        if g == GestureType.SWIPE_RIGHT:
            return ActionIntent(
                intent_type=IntentType.WINDOW_NEXT,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.SWIPE_LEFT:
            return ActionIntent(
                intent_type=IntentType.WINDOW_PREV,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 2. Window Minimize / Maximize (Simple Thumbs or Swipes)
        if g in (GestureType.THUMBS_UP, GestureType.SWIPE_UP):
            return ActionIntent(
                intent_type=IntentType.WINDOW_MAXIMIZE,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=g,
            )
        elif g in (GestureType.THUMBS_DOWN, GestureType.SWIPE_DOWN):
            return ActionIntent(
                intent_type=IntentType.WINDOW_MINIMIZE,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=g,
            )

        return None
