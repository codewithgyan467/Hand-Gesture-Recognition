"""Mouse interaction mode translating hand movements to pointer moves, clicks, drags, and scrolling."""

from __future__ import annotations
import time
from typing import Optional
from app.modes.base_mode import BaseMode
from app.core.types import (
    InteractionMode,
    GestureType,
    GestureRecognitionResult,
    HandLandmarks,
    HandFeatures,
    Handedness,
    ActionIntent,
    IntentType,
    HandLandmarkIndex,
)
from app.cursor.cursor_engine import CursorEngine
from app.gestures.pinch_engine import PinchEngine, PinchEvent
from app.core.config import PinchConfig


class MouseMode(BaseMode):
    """Primary desktop pointer mode handling smooth cursor tracking, clicks, dragging, and wheel scrolling."""

    def __init__(self, cursor_engine: CursorEngine, pinch_config: Optional[PinchConfig] = None) -> None:
        super().__init__(InteractionMode.MOUSE, cursor_engine)
        self.pinch_engine = PinchEngine(pinch_config)
        self._last_scroll_y: Optional[float] = None
        self._last_scroll_time: float = 0.0
        self._fist_active: bool = False
        self._last_fist_click_time: float = 0.0
        self._fist_cooldown_sec: float = 0.30

    def _is_right_hand(self, hand: HandLandmarks) -> bool:
        if hand.handedness == Handedness.RIGHT:
            return True
        if hand.handedness == Handedness.LEFT:
            return False
        # Fallback if unknown: compare thumb tip vs pinky tip in normalized frame
        try:
            thumb = hand.get(HandLandmarkIndex.THUMB_TIP)
            pinky = hand.get(HandLandmarkIndex.PINKY_TIP)
            return thumb.x < pinky.x
        except Exception:
            return True

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
        secondary_result: Optional[GestureRecognitionResult] = None,
        secondary_landmarks: Optional[HandLandmarks] = None,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # Map current cursor point
        index_tip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP).as_2d()
        screen_x, screen_y = self.cursor_engine.map_hand_to_screen(index_tip, timestamp)

        # 1. Update Pinch Engine with position for movement-based drag intent
        pinch_event = self.pinch_engine.update(
            features.thumb_index_dist, timestamp, cursor_pos=(screen_x, screen_y)
        )

        # 2. Check Pinch Events First
        if pinch_event == PinchEvent.CLICK:
            return ActionIntent(
                intent_type=IntentType.LEFT_CLICK,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.PINCH_INDEX,
            )
        elif pinch_event == PinchEvent.DOUBLE_CLICK:
            return ActionIntent(
                intent_type=IntentType.DOUBLE_CLICK,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.PINCH_HOLD,
            )
        elif pinch_event == PinchEvent.DRAG_START:
            return ActionIntent(
                intent_type=IntentType.DRAG_START,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif pinch_event == PinchEvent.DRAG_MOVE:
            return ActionIntent(
                intent_type=IntentType.DRAG_MOVE,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        elif pinch_event == PinchEvent.DRAG_END:
            return ActionIntent(
                intent_type=IntentType.DRAG_END,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 3. Check Fist / Punch Gesture
        # Right hand fist/punch -> Right click
        # Left hand fist/punch -> Left click
        fist_hand: Optional[HandLandmarks] = None
        fist_res: Optional[GestureRecognitionResult] = None

        if secondary_result is not None and secondary_result.gesture == GestureType.FIST and secondary_landmarks is not None:
            fist_hand = secondary_landmarks
            fist_res = secondary_result
        elif g == GestureType.FIST:
            fist_hand = landmarks
            fist_res = gesture_result

        if fist_hand is not None:
            if not self._fist_active and (timestamp - self._last_fist_click_time) >= self._fist_cooldown_sec:
                self._fist_active = True
                self._last_fist_click_time = timestamp

                is_right = self._is_right_hand(fist_hand)
                click_intent_type = IntentType.RIGHT_CLICK if is_right else IntentType.LEFT_CLICK
                conf = fist_res.confidence if fist_res else 0.95

                return ActionIntent(
                    intent_type=click_intent_type,
                    params={"x": screen_x, "y": screen_y},
                    confidence=conf,
                    timestamp=timestamp,
                    source_gesture=GestureType.FIST,
                )
            # Fist is held down: safely pause cursor movement and suppress click spam
            return None
        else:
            self._fist_active = False

        # 4. Right Click (Thumb + Middle Finger Pinch)
        if g == GestureType.PINCH_MIDDLE:
            return ActionIntent(
                intent_type=IntentType.RIGHT_CLICK,
                params={"x": screen_x, "y": screen_y},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
                source_gesture=GestureType.PINCH_MIDDLE,
            )

        # 5. Thumbs Up / Down Smooth Scrolling (Simple Gesture UX)
        if g in (GestureType.THUMBS_UP, GestureType.THUMBS_DOWN):
            if timestamp - self._last_scroll_time >= 0.08:  # Controlled 12 Hz rate-limit
                direction = 1 if g == GestureType.THUMBS_UP else -1  # 1 = up, -1 = down
                self._last_scroll_time = timestamp
                return ActionIntent(
                    intent_type=IntentType.SCROLL_VERTICAL,
                    params={"dy": direction * 2},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=g,
                )
            return None

        # 6. Two-Finger Scroll (Alternative / Advanced gesture)
        if g == GestureType.SCROLL:
            curr_y = index_tip.y
            dy = 0
            if self._last_scroll_y is not None:
                delta_y = curr_y - self._last_scroll_y
                if abs(delta_y) > 0.008:
                    # Moving hand up -> scroll down; moving hand down -> scroll up
                    dy = -1 if delta_y > 0 else 1
            self._last_scroll_y = curr_y

            if dy != 0:
                return ActionIntent(
                    intent_type=IntentType.SCROLL_VERTICAL,
                    params={"dy": dy * 2},
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    source_gesture=GestureType.SCROLL,
                )
            return None
        else:
            self._last_scroll_y = None

        # 7. Standard Pointer Move
        # Natural Hand Mouse: Any non-fist, non-scrolling hand pose (Open Palm, Pointer, Peace, or Casual)
        # guides the mouse cursor smoothly across the screen, as long as pinch is not active.
        if g != GestureType.FIST and not self.pinch_engine.is_pinched:
            return ActionIntent(
                intent_type=IntentType.MOUSE_MOVE,
                params={"x": screen_x, "y": screen_y},
                confidence=max(0.70, gesture_result.confidence),
                timestamp=timestamp,
                source_gesture=g,
            )

        return None

    def handle_hand_lost(self, timestamp: float) -> Optional[ActionIntent]:
        """Safely cleans up any active drag or scroll state if hand leaves camera view."""
        self._last_scroll_y = None
        self._fist_active = False
        if self.pinch_engine.is_dragging:
            self.pinch_engine.reset()
            return ActionIntent(
                intent_type=IntentType.DRAG_END,
                params={},
                confidence=1.0,
                timestamp=timestamp,
                source_gesture=GestureType.NONE,
            )
        self.pinch_engine.reset()
        return None

    def on_exit(self) -> None:
        self.pinch_engine.reset()
        self._last_scroll_y = None
        self._fist_active = False
        self._last_fist_click_time = 0.0
