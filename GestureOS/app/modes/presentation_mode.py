"""Presentation mode optimized for PowerPoint, Google Slides, Keynote, and PDF slideshows."""

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
    HandLandmarkIndex,
)
from app.cursor.cursor_engine import CursorEngine


class PresentationMode(BaseMode):
    """Presentation controller mode designed for seamless slide navigation and pointer control."""

    def __init__(self, cursor_engine: CursorEngine) -> None:
        super().__init__(InteractionMode.PRESENTATION, cursor_engine)

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # 1. Slide Navigation
        if g == GestureType.SWIPE_RIGHT:
            return ActionIntent(
                intent_type=IntentType.PRESENTATION_NEXT,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.SWIPE_LEFT:
            return ActionIntent(
                intent_type=IntentType.PRESENTATION_PREV,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 2. Start / Stop Slideshow
        if g == GestureType.THUMBS_UP:
            return ActionIntent(
                intent_type=IntentType.PRESENTATION_START,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.FIST and gesture_result.confidence >= 0.92:
            return ActionIntent(
                intent_type=IntentType.PRESENTATION_STOP,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 3. Virtual Pointer / Laser Pointer (Pointer finger or Open Palm)
        if g in (GestureType.POINTER, GestureType.OPEN_PALM):
            index_tip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP).as_2d()
            screen_x, screen_y = self.cursor_engine.map_hand_to_screen(index_tip, timestamp)
            return ActionIntent(
                intent_type=IntentType.MOUSE_MOVE,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        return None
