"""Abstract BaseMode defining how each interaction mode maps hand gestures to ActionIntents."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    GestureRecognitionResult,
    ActionIntent,
    InteractionMode,
)
from app.cursor.cursor_engine import CursorEngine


class BaseMode(ABC):
    """Abstract Base Class for interaction modes."""

    def __init__(self, mode_name: InteractionMode, cursor_engine: CursorEngine) -> None:
        self.mode_name = mode_name
        self.cursor_engine = cursor_engine

    @abstractmethod
    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
        secondary_result: Optional[GestureRecognitionResult] = None,
        secondary_landmarks: Optional[HandLandmarks] = None,
    ) -> Optional[ActionIntent]:
        """Translates recognized hand gesture and features into a mode-specific ActionIntent."""
        pass

    def on_enter(self) -> None:
        """Called when this mode becomes active."""
        pass

    def on_exit(self) -> None:
        """Called when this mode is deactivated."""
        pass
