"""Two-Hand Coordination Engine handling dual-hand gestures and hand role assignment."""

from __future__ import annotations
import math
import time
from typing import List, Optional, Tuple, Dict, Any
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Handedness,
    GestureType,
    GestureRecognitionResult,
    IntentType,
    ActionIntent,
)
from app.vision.feature_extractor import FeatureExtractor


class TwoHandCoordinator:
    """Coordinates two-hand interactions, dual gestures (e.g. dual fists, hands expanding), and role separation."""

    def __init__(self) -> None:
        self._last_interhand_distance: Optional[float] = None
        self._last_dual_gesture_time: float = 0.0

    def process_hands(
        self,
        hands: List[Tuple[HandLandmarks, HandFeatures, GestureRecognitionResult]],
        timestamp: Optional[float] = None,
    ) -> Optional[ActionIntent]:
        """Evaluates pair of hands for dual gestures. Returns ActionIntent if dual gesture detected."""
        if timestamp is None:
            timestamp = time.time()

        if len(hands) < 2:
            self._last_interhand_distance = None
            return None

        hand_a_lm, hand_a_feat, hand_a_res = hands[0]
        hand_b_lm, hand_b_feat, hand_b_res = hands[1]

        # 1. DUAL FISTS -> Global Emergency Stop Trigger!
        if hand_a_res.gesture == GestureType.FIST and hand_b_res.gesture == GestureType.FIST:
            return ActionIntent(
                intent_type=IntentType.EMERGENCY_STOP_TRIGGER,
                params={"reason": "Dual fists safety gesture triggered"},
                confidence=0.99,
                timestamp=timestamp,
                source_gesture=GestureType.DUAL_FISTS,
            )

        # 2. Hands Moving Apart vs Together (Zoom or Maximize/Restore)
        dist = math.hypot(
            hand_a_feat.palm_center.x - hand_b_feat.palm_center.x,
            hand_a_feat.palm_center.y - hand_b_feat.palm_center.y,
        )

        intent: Optional[ActionIntent] = None
        if self._last_interhand_distance is not None:
            delta = dist - self._last_interhand_distance
            # Rate limit inter-hand zoom/window gestures
            if (timestamp - self._last_dual_gesture_time) > 0.6:
                # Both hands moving apart (> 0.12 normalized distance jump)
                if delta > 0.12 and dist > 0.40:
                    intent = ActionIntent(
                        intent_type=IntentType.WINDOW_MAXIMIZE,
                        confidence=0.88,
                        timestamp=timestamp,
                    )
                    self._last_dual_gesture_time = timestamp
                # Both hands moving together (< -0.12 normalized distance jump)
                elif delta < -0.12 and dist < 0.35:
                    intent = ActionIntent(
                        intent_type=IntentType.WINDOW_RESTORE,
                        confidence=0.88,
                        timestamp=timestamp,
                    )
                    self._last_dual_gesture_time = timestamp

        self._last_interhand_distance = dist
        return intent

    def assign_roles(
        self, hands: List[HandLandmarks]
    ) -> Dict[str, Optional[HandLandmarks]]:
        """Assigns 'pointer_hand' and 'command_hand' based on handedness."""
        roles: Dict[str, Optional[HandLandmarks]] = {
            "pointer_hand": None,
            "command_hand": None,
        }

        if not hands:
            return roles

        if len(hands) == 1:
            # Single hand acts as pointer
            roles["pointer_hand"] = hands[0]
            return roles

        for h in hands:
            if h.handedness == Handedness.RIGHT:
                roles["pointer_hand"] = h
            elif h.handedness == Handedness.LEFT:
                roles["command_hand"] = h

        # Fallback if both unknown
        if roles["pointer_hand"] is None and len(hands) > 0:
            roles["pointer_hand"] = hands[0]
        if roles["command_hand"] is None and len(hands) > 1:
            roles["command_hand"] = hands[1]

        return roles
