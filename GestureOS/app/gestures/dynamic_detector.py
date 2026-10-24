"""Temporal buffer and trajectory-based dynamic gesture recognizer for swipes, waves, and circles."""

from __future__ import annotations
import math
import time
from collections import deque
from typing import List, Tuple, Optional
from app.core.types import (
    Point2D,
    GestureType,
    GestureRecognitionResult,
    HandLandmarks,
    HandFeatures,
)
from app.core.config import GestureValidationConfig


class DynamicGestureDetector:
    """Recognizes temporal trajectory gestures (swipes, waves, circular motion) over rolling time window."""

    def __init__(
        self,
        validation_config: Optional[GestureValidationConfig] = None,
        buffer_duration_sec: float = 0.55,
        invert_x: bool = False,
    ) -> None:
        self.config = validation_config or GestureValidationConfig()
        self.buffer_duration_sec = buffer_duration_sec
        self.invert_x = invert_x
        # Buffer of (timestamp, Point2D, HandFeatures)
        self._buffer: deque = deque(maxlen=30)
        self._last_detected_time: float = 0.0

    def update(
        self,
        point: Point2D,
        features: HandFeatures,
        landmarks: HandLandmarks,
        timestamp: Optional[float] = None,
    ) -> GestureRecognitionResult:
        if timestamp is None:
            timestamp = time.time()

        self._buffer.append((timestamp, point, features, landmarks))
        self._prune_old_entries(timestamp)

        # Enforce minimum cooldown between dynamic gesture triggers
        if timestamp - self._last_detected_time < 0.45:
            return GestureRecognitionResult(gesture=GestureType.NONE, confidence=0.0)

        # Must have sufficient frames in the window
        if len(self._buffer) < 6:
            return GestureRecognitionResult(gesture=GestureType.NONE, confidence=0.0)

        t_start, p_start, _, _ = self._buffer[0]
        t_end, p_end, f_end, l_end = self._buffer[-1]
        dt = t_end - t_start

        if dt < 0.15:
            return GestureRecognitionResult(gesture=GestureType.NONE, confidence=0.0)

        dx = p_end.x - p_start.x
        dy = p_end.y - p_start.y
        disp = math.hypot(dx, dy)
        vel = disp / dt

        # Compute total path length
        path_len = 0.0
        for i in range(1, len(self._buffer)):
            _, p_prev, _, _ = self._buffer[i - 1]
            _, p_curr, _, _ = self._buffer[i]
            path_len += math.hypot(p_curr.x - p_prev.x, p_curr.y - p_prev.y)

        straightness = disp / max(1e-4, path_len)

        # 1. SWIPE DETECTION (High velocity, high straightness, minimum distance)
        min_dist = self.config.swipe_min_distance
        min_vel = self.config.swipe_min_velocity

        if disp >= min_dist and vel >= min_vel and straightness >= 0.70:
            # Horizontal swipe dominance
            if abs(dx) > abs(dy) * 1.4:
                effective_dx = -dx if self.invert_x else dx
                g = GestureType.SWIPE_RIGHT if effective_dx > 0 else GestureType.SWIPE_LEFT
                self._last_detected_time = timestamp
                self._buffer.clear()
                return GestureRecognitionResult(
                    gesture=g,
                    confidence=min(1.0, 0.75 + (vel / (min_vel * 2.0)) * 0.25),
                    hand_features=f_end,
                    handedness=l_end.handedness,
                    raw_landmarks=l_end,
                    timestamp=timestamp,
                    metadata={"velocity": vel, "distance": disp},
                )
            # Vertical swipe dominance
            elif abs(dy) > abs(dx) * 1.4:
                g = GestureType.SWIPE_DOWN if dy > 0 else GestureType.SWIPE_UP
                self._last_detected_time = timestamp
                self._buffer.clear()
                return GestureRecognitionResult(
                    gesture=g,
                    confidence=min(1.0, 0.75 + (vel / (min_vel * 2.0)) * 0.25),
                    hand_features=f_end,
                    handedness=l_end.handedness,
                    raw_landmarks=l_end,
                    timestamp=timestamp,
                    metadata={"velocity": vel, "distance": disp},
                )

        # 2. WAVE DETECTION (Oscillations in x-direction with open palm)
        if f_end.finger_extended["index"] and f_end.finger_extended["middle"]:
            sign_reversals = 0
            last_sign = 0
            for i in range(1, len(self._buffer)):
                _, p1, _, _ = self._buffer[i - 1]
                _, p2, _, _ = self._buffer[i]
                step_dx = p2.x - p1.x
                if abs(step_dx) > 0.015:
                    current_sign = 1 if step_dx > 0 else -1
                    if last_sign != 0 and current_sign != last_sign:
                        sign_reversals += 1
                    last_sign = current_sign

            if sign_reversals >= self.config.wave_oscillations_required and path_len > 0.20:
                self._last_detected_time = timestamp
                self._buffer.clear()
                return GestureRecognitionResult(
                    gesture=GestureType.WAVE,
                    confidence=0.88,
                    hand_features=f_end,
                    handedness=l_end.handedness,
                    raw_landmarks=l_end,
                    timestamp=timestamp,
                    metadata={"reversals": sign_reversals},
                )

        return GestureRecognitionResult(gesture=GestureType.NONE, confidence=0.0)

    def _prune_old_entries(self, current_time: float) -> None:
        while self._buffer and (current_time - self._buffer[0][0]) > self.buffer_duration_sec:
            self._buffer.popleft()

    def reset(self) -> None:
        self._buffer.clear()
        self._last_detected_time = 0.0
