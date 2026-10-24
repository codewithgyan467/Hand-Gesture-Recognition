"""MediaPipe Tasks HandLandmarker detector wrapper for GestureOS."""

from __future__ import annotations
import os
import time
import threading
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from typing import List, Optional, Tuple, Any
from app.core.types import HandLandmarks, Point3D, Handedness
from app.diagnostics.logger import get_logger

logger = get_logger("detector")


class HandDetector:
    """Detects and tracks hands using Google MediaPipe Tasks API."""

    def __init__(
        self,
        model_path: str = "models/hand_landmarker.task",
        num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.model_path = model_path
        self.num_hands = num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        self._landmarker: Optional[vision.HandLandmarker] = None
        self._lock = threading.Lock()
        self._last_timestamp_ms: int = 0
        self._is_initialized = False

        self._init_detector()

    def _resolve_model_path(self, path: str) -> str:
        if os.path.isabs(path) and os.path.exists(path):
            return path
        if os.path.exists(path):
            return os.path.abspath(path)

        # Delegate to unified ResourceManager
        try:
            from app.core.resources import get_resource_manager
            rm_model = get_resource_manager().get_hand_model_path()
            if rm_model.exists():
                return str(rm_model)
        except Exception:
            pass

        # Relative to module's package
        pkg_model = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", path))
        if os.path.exists(pkg_model):
            return pkg_model

        return path

    def _init_detector(self) -> bool:
        resolved = self._resolve_model_path(self.model_path)
        if not os.path.exists(resolved):
            logger.error(f"MediaPipe hand landmarker model not found at: {self.model_path} (resolved: {resolved})")
            return False
        self.model_path = resolved

        try:
            options = vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=self.num_hands,
                min_hand_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)
            self._is_initialized = True
            logger.info("MediaPipe HandLandmarker initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe HandLandmarker: {e}", exc_info=True)
            self._landmarker = None
            self._is_initialized = False
            return False

    def detect(self, frame_bgr: np.ndarray) -> List[HandLandmarks]:
        """Detects hands in a BGR frame and returns a list of HandLandmarks."""
        if not self._is_initialized or self._landmarker is None:
            return []

        if frame_bgr is None or frame_bgr.size == 0:
            return []

        with self._lock:
            try:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                # Ensure strictly increasing timestamp for VIDEO running mode
                now_ms = int(time.time() * 1000)
                if now_ms <= self._last_timestamp_ms:
                    now_ms = self._last_timestamp_ms + 1
                self._last_timestamp_ms = now_ms

                result = self._landmarker.detect_for_video(mp_image, now_ms)
                return self._parse_result(result, now_ms)
            except Exception as e:
                logger.error(f"Error during hand detection: {e}")
                return []

    def _parse_result(self, result: Any, timestamp_ms: int) -> List[HandLandmarks]:
        if not result or not result.hand_landmarks:
            return []

        hands_list: List[HandLandmarks] = []
        for i, raw_landmarks in enumerate(result.hand_landmarks):
            points = [
                Point3D(x=lm.x, y=lm.y, z=lm.z)
                for lm in raw_landmarks
            ]

            # Handedness parsing
            handedness = Handedness.UNKNOWN
            score = 0.0
            if result.handedness and i < len(result.handedness):
                categories = result.handedness[i]
                if categories:
                    category = categories[0]
                    # Note: MediaPipe returns mirrored handedness for self-view
                    category_name = category.category_name
                    score = category.score
                    if category_name == "Left":
                        handedness = Handedness.LEFT
                    elif category_name == "Right":
                        handedness = Handedness.RIGHT

            hands_list.append(
                HandLandmarks(
                    landmarks=points,
                    handedness=handedness,
                    score=score,
                    timestamp_ms=float(timestamp_ms),
                )
            )

        return hands_list

    def close(self) -> None:
        with self._lock:
            if self._landmarker:
                try:
                    self._landmarker.close()
                except Exception:
                    pass
                self._landmarker = None
                self._is_initialized = False
                logger.info("Hand detector closed.")
