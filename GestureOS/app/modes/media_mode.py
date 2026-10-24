"""Media and volume control interaction mode."""

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


class MediaMode(BaseMode):
    """Media playback mode translating simple gestures and swipes to track and volume controls."""

    def __init__(self, cursor_engine: CursorEngine) -> None:
        super().__init__(InteractionMode.MEDIA, cursor_engine)
        self._last_volume_dist: Optional[float] = None
        self._last_step_volume_time: float = 0.0
        self.current_volume: float = 50.0

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # 1. Simple Gesture Vocabulary: Volume Up (👍) & Volume Down (👎)
        if g == GestureType.THUMBS_UP:
            if timestamp - self._last_step_volume_time >= 0.08:  # Controlled 12 Hz rate-limit
                self._last_step_volume_time = timestamp
                self.current_volume = min(100.0, self.current_volume + 3.0)
                return ActionIntent(
                    intent_type=IntentType.VOLUME_SET,
                    params={"level": round(self.current_volume, 1)},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=GestureType.THUMBS_UP,
                )
            return None

        if g == GestureType.THUMBS_DOWN:
            if timestamp - self._last_step_volume_time >= 0.08:
                self._last_step_volume_time = timestamp
                self.current_volume = max(0.0, self.current_volume - 3.0)
                return ActionIntent(
                    intent_type=IntentType.VOLUME_SET,
                    params={"level": round(self.current_volume, 1)},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=GestureType.THUMBS_DOWN,
                )
            return None

        # 2. Simple Secondary Action: Play / Pause (✌ Peace gesture)
        if g == GestureType.PEACE:
            return ActionIntent(
                intent_type=IntentType.MEDIA_PLAY_PAUSE,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.PEACE,
            )

        # 3. Track Navigation (Swipes Left / Right)
        if g == GestureType.SWIPE_RIGHT:
            return ActionIntent(
                intent_type=IntentType.MEDIA_NEXT,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.SWIPE_RIGHT,
            )
        elif g == GestureType.SWIPE_LEFT:
            return ActionIntent(
                intent_type=IntentType.MEDIA_PREV,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.SWIPE_LEFT,
            )

        # 4. Open Palm for Play / Pause
        if g == GestureType.OPEN_PALM and gesture_result.confidence >= 0.88:
            return ActionIntent(
                intent_type=IntentType.MEDIA_PLAY_PAUSE,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.OPEN_PALM,
            )

        # 5. Continuous Aperture Volume (Thumb + Index aperture distance)
        if features.finger_extended["thumb"] and features.finger_extended["index"] and not features.finger_extended["middle"]:
            dist = features.thumb_index_dist
            norm_vol = max(0.0, min(100.0, ((dist - 0.28) / 0.80) * 100.0))
            self.current_volume = norm_vol

            return ActionIntent(
                intent_type=IntentType.VOLUME_SET,
                params={"level": round(self.current_volume, 1)},
                confidence=0.90,
                timestamp=timestamp,
            )

        # 6. Mode pointer tracking (Pointer)
        if g == GestureType.POINTER:
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
        self._last_volume_dist = None
        self._last_step_volume_time = 0.0
