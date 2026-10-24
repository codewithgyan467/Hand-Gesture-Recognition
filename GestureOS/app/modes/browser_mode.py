"""Browser navigation mode for web browsing shortcuts."""

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
    Handedness,
)
from app.cursor.cursor_engine import CursorEngine


class BrowserMode(BaseMode):
    """Web browser interaction mode mapping swipes and hand poses to tab and history controls."""

    def __init__(self, cursor_engine: CursorEngine) -> None:
        super().__init__(InteractionMode.BROWSER, cursor_engine)
        self._last_scroll_y: Optional[float] = None
        self._last_scroll_time: float = 0.0
        self._last_nav_time: float = 0.0

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # 1. Simple Gesture Vocabulary: Scroll Up (👍) & Scroll Down (👎)
        if g in (GestureType.THUMBS_UP, GestureType.THUMBS_DOWN):
            if timestamp - self._last_scroll_time >= 0.08:
                direction = 1 if g == GestureType.THUMBS_UP else -1
                self._last_scroll_time = timestamp
                return ActionIntent(
                    intent_type=IntentType.SCROLL_VERTICAL,
                    params={"dy": direction * 3},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=g,
                )
            return None

        # 2. Simple Secondary Action: New Tab (✌ Peace gesture)
        if g == GestureType.PEACE:
            return ActionIntent(
                intent_type=IntentType.BROWSER_NEW_TAB,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.PEACE,
            )

        # 3. Simple Fist Commands: Right Fist = Back, Left Fist = Forward
        if g == GestureType.FIST:
            if timestamp - self._last_nav_time >= 0.40:
                self._last_nav_time = timestamp
                is_right = (landmarks.handedness == Handedness.RIGHT)
                nav_intent = IntentType.BROWSER_BACK if is_right else IntentType.BROWSER_FORWARD
                return ActionIntent(
                    intent_type=nav_intent,
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=GestureType.FIST,
                )
            return None

        # 4. Swipes for Navigation (Advanced / Directional gesture)
        if g == GestureType.SWIPE_LEFT:
            return ActionIntent(
                intent_type=IntentType.BROWSER_BACK,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.SWIPE_RIGHT:
            return ActionIntent(
                intent_type=IntentType.BROWSER_FORWARD,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.SWIPE_UP:
            return ActionIntent(
                intent_type=IntentType.BROWSER_PAGE_DOWN,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif g == GestureType.SWIPE_DOWN:
            return ActionIntent(
                intent_type=IntentType.BROWSER_PAGE_UP,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 5. Two-Finger Scroll
        if g == GestureType.SCROLL:
            curr_y = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP).y
            dy = 0
            if self._last_scroll_y is not None:
                delta = curr_y - self._last_scroll_y
                if abs(delta) > 0.008:
                    dy = -1 if delta > 0 else 1
            self._last_scroll_y = curr_y

            if dy != 0:
                return ActionIntent(
                    intent_type=IntentType.SCROLL_VERTICAL,
                    params={"dy": dy * 3},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                )
        else:
            self._last_scroll_y = None

        # 6. Cursor Move (Pointer / Open Hand)
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

    def on_exit(self) -> None:
        self._last_scroll_y = None
