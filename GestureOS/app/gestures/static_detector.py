"""Deterministic geometric static hand gesture detector."""

from __future__ import annotations
import math
import time
from typing import Optional
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    GestureType,
    GestureRecognitionResult,
    HandLandmarkIndex,
    Handedness,
)
from app.core.config import PinchConfig


class StaticGestureDetector:
    """Classifies deterministic hand poses from normalized hand features."""

    def __init__(self, pinch_config: Optional[PinchConfig] = None) -> None:
        self.pinch_config = pinch_config or PinchConfig()

    def detect(self, landmarks: HandLandmarks, features: HandFeatures) -> GestureRecognitionResult:
        now = time.time()
        ext = features.finger_extended

        # 1. Check FIST (all fingers curled)
        if not ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"] and not ext["thumb"]:
            return GestureRecognitionResult(
                gesture=GestureType.FIST,
                confidence=0.95,
                hand_features=features,
                handedness=landmarks.handedness,
                raw_landmarks=landmarks,
                timestamp=now,
            )

        # 2. Check OPEN PALM (all fingers extended)
        if ext["thumb"] and ext["index"] and ext["middle"] and ext["ring"] and ext["pinky"]:
            return GestureRecognitionResult(
                gesture=GestureType.OPEN_PALM,
                confidence=0.96,
                hand_features=features,
                handedness=landmarks.handedness,
                raw_landmarks=landmarks,
                timestamp=now,
            )

        # 3. Check PINCH_MIDDLE (Thumb + Middle finger pinch -> Right Click)
        # Prioritize middle pinch if thumb_middle_dist is smaller than thumb_index_dist
        if features.thumb_middle_dist <= self.pinch_config.pinch_threshold:
            confidence = max(0.6, 1.0 - (features.thumb_middle_dist / self.pinch_config.pinch_threshold) * 0.4)
            return GestureRecognitionResult(
                gesture=GestureType.PINCH_MIDDLE,
                confidence=confidence,
                hand_features=features,
                handedness=landmarks.handedness,
                raw_landmarks=landmarks,
                timestamp=now,
                metadata={"distance": features.thumb_middle_dist},
            )

        # 4. Check PINCH_INDEX (Thumb + Index pinch -> Left Click / Drag)
        if features.thumb_index_dist <= self.pinch_config.pinch_threshold:
            confidence = max(0.6, 1.0 - (features.thumb_index_dist / self.pinch_config.pinch_threshold) * 0.4)
            return GestureRecognitionResult(
                gesture=GestureType.PINCH_INDEX,
                confidence=confidence,
                hand_features=features,
                handedness=landmarks.handedness,
                raw_landmarks=landmarks,
                timestamp=now,
                metadata={"distance": features.thumb_index_dist},
            )

        # 5. Check SCROLL (Two fingers: Index and Middle extended together, ring & pinky curled)
        if ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
            # Distance between index tip and middle tip
            p_index = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP)
            p_middle = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_TIP)
            tip_dist = math.hypot(p_index.x - p_middle.x, p_index.y - p_middle.y) / features.hand_scale

            if tip_dist < 0.45:
                # Fingers close together -> SCROLL
                return GestureRecognitionResult(
                    gesture=GestureType.SCROLL,
                    confidence=0.92,
                    hand_features=features,
                    handedness=landmarks.handedness,
                    raw_landmarks=landmarks,
                    timestamp=now,
                    metadata={"scroll_tip_dist": tip_dist},
                )
            else:
                # Fingers separated in V shape -> PEACE / VICTORY
                return GestureRecognitionResult(
                    gesture=GestureType.PEACE,
                    confidence=0.88,
                    hand_features=features,
                    handedness=landmarks.handedness,
                    raw_landmarks=landmarks,
                    timestamp=now,
                )

        # 6. Check THUMBS_UP / THUMBS_DOWN (Only thumb extended)
        if ext["thumb"] and not ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"]:
            thumb_tip = landmarks.get(HandLandmarkIndex.THUMB_TIP)
            wrist = landmarks.get(HandLandmarkIndex.WRIST)
            if thumb_tip.y < wrist.y:
                return GestureRecognitionResult(
                    gesture=GestureType.THUMBS_UP,
                    confidence=0.92,
                    hand_features=features,
                    handedness=landmarks.handedness,
                    raw_landmarks=landmarks,
                    timestamp=now,
                )
            elif thumb_tip.y > wrist.y:
                return GestureRecognitionResult(
                    gesture=GestureType.THUMBS_DOWN,
                    confidence=0.92,
                    hand_features=features,
                    handedness=landmarks.handedness,
                    raw_landmarks=landmarks,
                    timestamp=now,
                )

        # 7. Check POINTER (Index finger extended, other fingers curled)
        if ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"]:
            return GestureRecognitionResult(
                gesture=GestureType.POINTER,
                confidence=0.94,
                hand_features=features,
                handedness=landmarks.handedness,
                raw_landmarks=landmarks,
                timestamp=now,
            )

        return GestureRecognitionResult(
            gesture=GestureType.NONE,
            confidence=0.0,
            hand_features=features,
            handedness=landmarks.handedness,
            raw_landmarks=landmarks,
            timestamp=now,
        )
