"""Interactive 8-step calibration wizard engine tuning tracking and thresholds to the user's hand."""

from __future__ import annotations
import math
import time
from enum import Enum, auto
from typing import Dict, Any, Optional, List
from app.core.config import GestureOSConfig
from app.core.types import HandLandmarks, HandFeatures, GestureType


class CalibrationStep(int, Enum):
    CAMERA_POSITION = 1
    HAND_DETECTION = 2
    ACTIVE_REGION = 3
    CURSOR_RANGE = 4
    PINCH_CALIBRATION = 5
    GESTURE_VERIFICATION = 6
    SENSITIVITY = 7
    FINAL_TEST = 8
    COMPLETED = 9


class CalibrationWizardEngine:
    """Orchestrates interactive calibration steps and personalizes tracking parameters."""

    def __init__(self, target_config: GestureOSConfig) -> None:
        self.config = target_config
        self.current_step = CalibrationStep.CAMERA_POSITION
        self.step_progress: float = 0.0
        self.instruction_text: str = ""

        # Calibration recorded data buffers
        self._hand_samples: List[HandLandmarks] = []
        self._recorded_pinch_distances: List[float] = []
        self._recorded_open_distances: List[float] = []
        self._corner_points: List[Tuple[float, float]] = []

        self._set_step_instructions()

    def advance_step(self) -> CalibrationStep:
        """Transitions to the next calibration step."""
        if self.current_step.value < CalibrationStep.COMPLETED.value:
            self.current_step = CalibrationStep(self.current_step.value + 1)
            self.step_progress = 0.0
            self._set_step_instructions()
        return self.current_step

    def previous_step(self) -> CalibrationStep:
        """Transitions back to previous step."""
        if self.current_step.value > CalibrationStep.CAMERA_POSITION.value:
            self.current_step = CalibrationStep(self.current_step.value - 1)
            self.step_progress = 0.0
            self._set_step_instructions()
        return self.current_step

    def update_with_frame(
        self,
        hands: List[HandLandmarks],
        features: Optional[HandFeatures],
    ) -> Dict[str, Any]:
        """Feeds live hand tracking data into the active calibration step."""
        status = {
            "step": self.current_step.value,
            "step_name": self.current_step.name,
            "instruction": self.instruction_text,
            "progress": self.step_progress,
            "is_step_ready": False,
        }

        if not hands or features is None:
            return status

        primary_hand = hands[0]

        # Step 2: Hand Detection Quality
        if self.current_step == CalibrationStep.HAND_DETECTION:
            if primary_hand.score > 0.80:
                self.step_progress = min(1.0, self.step_progress + 0.05)
                if self.step_progress >= 1.0:
                    status["is_step_ready"] = True

        # Step 3: Active Control Region
        elif self.current_step == CalibrationStep.ACTIVE_REGION:
            cx = features.palm_center.x
            cy = features.palm_center.y
            self._corner_points.append((cx, cy))
            if len(self._corner_points) > 40:
                xs = [p[0] for p in self._corner_points]
                ys = [p[1] for p in self._corner_points]
                # Update active region bounds
                self.config.active_region.x_min = max(0.05, min(xs) - 0.03)
                self.config.active_region.x_max = min(0.95, max(xs) + 0.03)
                self.config.active_region.y_min = max(0.05, min(ys) - 0.03)
                self.config.active_region.y_max = min(0.95, max(ys) + 0.03)
                self.step_progress = 1.0
                status["is_step_ready"] = True

        # Step 5: Pinch Calibration
        elif self.current_step == CalibrationStep.PINCH_CALIBRATION:
            dist = features.thumb_index_dist
            self._recorded_pinch_distances.append(dist)
            if len(self._recorded_pinch_distances) >= 30:
                # Calculate natural pinch threshold
                min_pinch = min(self._recorded_pinch_distances)
                self.config.pinch.pinch_threshold = round(min_pinch + 0.06, 2)
                self.config.pinch.release_threshold = round(self.config.pinch.pinch_threshold + 0.08, 2)
                self.step_progress = 1.0
                status["is_step_ready"] = True

        return status

    def _set_step_instructions(self) -> None:
        instructions = {
            CalibrationStep.CAMERA_POSITION: "Step 1/8: Position your camera at eye level with good ambient lighting.",
            CalibrationStep.HAND_DETECTION: "Step 2/8: Hold your hand open in front of the camera until tracking stabilizes.",
            CalibrationStep.ACTIVE_REGION: "Step 3/8: Move your hand to top-left, top-right, bottom-left, and bottom-right to define your motion box.",
            CalibrationStep.CURSOR_RANGE: "Step 4/8: Move your pointer finger around the comfortable screen space.",
            CalibrationStep.PINCH_CALIBRATION: "Step 5/8: Pinch your thumb and index finger together and hold for 2 seconds.",
            CalibrationStep.GESTURE_VERIFICATION: "Step 6/8: Verify gestures: Pointer, Pinch Click, Two-Finger Scroll, and Fist.",
            CalibrationStep.SENSITIVITY: "Step 7/8: Select your preferred cursor smoothing (Low, Medium, or High).",
            CalibrationStep.FINAL_TEST: "Step 8/8: Calibration complete! Test your personalized touchless control.",
            CalibrationStep.COMPLETED: "Calibration Successfully Saved!",
        }
        self.instruction_text = instructions.get(self.current_step, "")
