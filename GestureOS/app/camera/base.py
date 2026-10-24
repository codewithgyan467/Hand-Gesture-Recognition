"""Abstract base camera interface for GestureOS."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict
import numpy as np


class BaseCamera(ABC):
    """Abstract Camera Interface."""

    @abstractmethod
    def start(self) -> bool:
        """Starts video capture."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops video capture and releases hardware resources."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Reads the latest frame from the capture stream. Returns (success, frame_bgr)."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Returns True if the camera is actively capturing frames."""
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Returns (width, height) of the capture stream."""
        pass

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> bool:
        """Configures capture stream resolution."""
        pass

    @abstractmethod
    def set_fps(self, fps: int) -> bool:
        """Configures capture stream target FPS."""
        pass

    @abstractmethod
    def get_camera_name(self) -> str:
        """Returns a human-readable identifier for the camera source."""
        pass
