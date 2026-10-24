"""Simulation camera generating synthetic video frames and hand test patterns for offline verification."""

from __future__ import annotations
import math
import time
import numpy as np
import cv2
from typing import Tuple, Optional
from app.camera.base import BaseCamera
from app.core.types import GestureType


class SimulationCamera(BaseCamera):
    """Synthetic camera generating clean test frames for headless CI, tests, and dry-run demos."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self._is_running = False
        self._frame_count = 0
        self._simulated_gesture = GestureType.POINTER

    def set_simulated_gesture(self, gesture: GestureType) -> None:
        self._simulated_gesture = gesture

    def start(self) -> bool:
        self._is_running = True
        self._frame_count = 0
        return True

    def stop(self) -> None:
        self._is_running = False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._is_running:
            self._is_running = True

        self._frame_count += 1
        # Create dark stylish gradient canvas
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:, :] = (24, 20, 20)  # Dark slate background

        # Draw a synthetic animated hand or circle
        t = self._frame_count / float(self.fps)
        cx = int(self.width / 2 + 100 * math.sin(t * 1.5))
        cy = int(self.height / 2 + 60 * math.cos(t * 1.5))

        # Render visual indicator of simulation state
        cv2.putText(
            frame,
            f"SIMULATION MODE - {self._simulated_gesture.value.upper()}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 220, 255),
            2,
        )
        cv2.circle(frame, (cx, cy), 14, (0, 255, 128), -1)
        cv2.circle(frame, (cx, cy), 28, (0, 255, 128), 2)

        return (True, frame)

    def is_opened(self) -> bool:
        return self._is_running

    def get_resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def set_resolution(self, width: int, height: int) -> bool:
        self.width = width
        self.height = height
        return True

    def set_fps(self, fps: int) -> bool:
        self.fps = fps
        return True

    def get_camera_name(self) -> str:
        return "GestureOS Synthetic Simulation Camera"
