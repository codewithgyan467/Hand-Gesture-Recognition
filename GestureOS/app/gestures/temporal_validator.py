"""Temporal validation, frame debouncing, confidence gating, and hysteresis engine for GestureOS."""

from __future__ import annotations
import time
from typing import Dict, Optional
from app.core.types import GestureType, GestureRecognitionResult
from app.core.config import GestureValidationConfig, CooldownConfig
from app.diagnostics.logger import get_logger

logger = get_logger("temporal_validator")


class TemporalValidator:
    """Ensures gestures are temporally stable over multiple frames before action emission."""

    def __init__(
        self,
        validation_config: Optional[GestureValidationConfig] = None,
        cooldown_config: Optional[CooldownConfig] = None,
    ) -> None:
        self.val_config = validation_config or GestureValidationConfig()
        self.cd_config = cooldown_config or CooldownConfig()

        self._candidate_gesture: GestureType = GestureType.NONE
        self._consecutive_count: int = 0
        self._candidate_start_time: float = 0.0

        # Last execution timestamp per gesture for cooldown tracking
        self._cooldown_expiry: Dict[GestureType, float] = {}

    def validate(self, raw_result: GestureRecognitionResult) -> Optional[GestureRecognitionResult]:
        """Validates raw gesture candidate against temporal consistency and cooldowns.
        
        Returns validated GestureRecognitionResult if passed, or None if filtered out.
        """
        now = time.time()
        gesture = raw_result.gesture

        # 1. Filter low confidence or NONE
        if gesture == GestureType.NONE or raw_result.confidence < self.val_config.min_confidence:
            self._reset_candidate()
            return None

        # Continuous tracking gestures (POINTER, SCROLL, OPEN_PALM, PEACE) do not require multi-frame discrete cooldowns
        if gesture in (GestureType.POINTER, GestureType.SCROLL, GestureType.OPEN_PALM, GestureType.PEACE):
            return raw_result

        # 2. Check Cooldown Expiry
        if gesture in self._cooldown_expiry:
            if now < self._cooldown_expiry[gesture]:
                # In active cooldown; suppress flutter
                return None

        # 3. Consecutive Frames Debounce
        if gesture == self._candidate_gesture:
            self._consecutive_count += 1
        else:
            self._candidate_gesture = gesture
            self._consecutive_count = 1
            self._candidate_start_time = now

        required_frames = self.val_config.consecutive_frames_required
        if self._consecutive_count >= required_frames:
            # Gesture validated! Start cooldown for discrete events
            self._apply_cooldown(gesture, now)
            validated = GestureRecognitionResult(
                gesture=gesture,
                confidence=raw_result.confidence,
                hand_features=raw_result.hand_features,
                handedness=raw_result.handedness,
                raw_landmarks=raw_result.raw_landmarks,
                timestamp=now,
                metadata=raw_result.metadata,
            )
            # Reset consecutive count so single trigger actions don't repeat endlessly
            self._consecutive_count = 0
            return validated

        return None

    def _apply_cooldown(self, gesture: GestureType, now: float) -> None:
        ms = 300 # default
        if gesture == GestureType.PINCH_INDEX:
            ms = self.cd_config.left_click_ms
        elif gesture == GestureType.PINCH_MIDDLE:
            ms = self.cd_config.right_click_ms
        elif gesture in (GestureType.SWIPE_LEFT, GestureType.SWIPE_RIGHT, GestureType.SWIPE_UP, GestureType.SWIPE_DOWN):
            ms = self.cd_config.swipe_ms

        self._cooldown_expiry[gesture] = now + (ms / 1000.0)

    def _reset_candidate(self) -> None:
        self._candidate_gesture = GestureType.NONE
        self._consecutive_count = 0
        self._candidate_start_time = 0.0

    def reset(self) -> None:
        self._reset_candidate()
        self._cooldown_expiry.clear()
