"""Multi-rate vision pipeline performance controller with adaptive inference decimation."""

from __future__ import annotations
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.diagnostics.logger import get_logger

logger = get_logger("performance")


@dataclass
class PerformanceTierSettings:
    tier_name: str
    target_camera_fps: int
    hand_inference_stride: int  # 1 = every frame, 2 = alternate frames
    study_inference_stride: int # 2 = 15 FPS on 30 FPS cam, 3 = 10 FPS, 5 = 6 FPS
    enable_full_skeletons: bool
    enable_bounding_boxes: bool
    max_frame_latency_ms: float


TIER_PROFILES: Dict[str, PerformanceTierSettings] = {
    "FULL": PerformanceTierSettings(
        tier_name="FULL",
        target_camera_fps=30,
        hand_inference_stride=1,
        study_inference_stride=2,  # 15 FPS study inference
        enable_full_skeletons=True,
        enable_bounding_boxes=True,
        max_frame_latency_ms=45.0,
    ),
    "BALANCED": PerformanceTierSettings(
        tier_name="BALANCED",
        target_camera_fps=30,
        hand_inference_stride=1,
        study_inference_stride=3,  # 10 FPS study inference
        enable_full_skeletons=True,
        enable_bounding_boxes=True,
        max_frame_latency_ms=50.0,
    ),
    "LIGHT": PerformanceTierSettings(
        tier_name="LIGHT",
        target_camera_fps=24,
        hand_inference_stride=1,
        study_inference_stride=4,  # 6 FPS study inference
        enable_full_skeletons=False,
        enable_bounding_boxes=True,
        max_frame_latency_ms=65.0,
    ),
    "COMPATIBILITY": PerformanceTierSettings(
        tier_name="COMPATIBILITY",
        target_camera_fps=15,
        hand_inference_stride=2,
        study_inference_stride=5,  # 3 FPS study inference
        enable_full_skeletons=False,
        enable_bounding_boxes=False,
        max_frame_latency_ms=80.0,
    ),
}


class PerformanceController:
    """Manages adaptive multi-rate inference execution to maintain rock-steady 30 FPS camera preview."""

    def __init__(self, tier_name: str = "BALANCED", tier: Optional[str] = None) -> None:
        chosen_tier = (tier or tier_name).upper()
        self.current_tier = TIER_PROFILES.get(chosen_tier, TIER_PROFILES["BALANCED"])
        self._frame_counter: int = 0
        self._study_frame_counter: int = 0
        self._last_frame_time: float = time.time()
        self._recent_latencies: list[float] = []
        self._recent_study_durations: list[float] = []
        self._dynamic_study_stride: int = self.current_tier.study_inference_stride
        self._dropped_frames_count: int = 0

    def record_study_guard_inference(self, duration_ms: float) -> None:
        self._recent_study_durations.append(duration_ms)
        if len(self._recent_study_durations) > 30:
            self._recent_study_durations.pop(0)

    def record_frame(self, latency_ms: float) -> None:
        self.record_frame_latency(latency_ms)

    def set_tier(self, tier_name: str) -> None:
        name = tier_name.upper()
        if name in TIER_PROFILES:
            self.current_tier = TIER_PROFILES[name]
            self._dynamic_study_stride = self.current_tier.study_inference_stride
            logger.info(f"PerformanceController switched to tier: {name}")

    def on_frame_start(self) -> None:
        self._frame_counter += 1

    def should_infer_hand(self) -> bool:
        """Determines if hand tracking should run on the current frame."""
        return (self._frame_counter % self.current_tier.hand_inference_stride) == 0

    def should_infer_study_guard(self) -> bool:
        """Determines if object and face models should execute on the current frame."""
        return (self._frame_counter % self._dynamic_study_stride) == 0

    def record_frame_latency(self, latency_ms: float) -> None:
        """Monitors end-to-end frame processing time and dynamically throttles heavy inference if needed."""
        self._recent_latencies.append(latency_ms)
        if len(self._recent_latencies) > 30:
            self._recent_latencies.pop(0)

        # Dynamic Adaptation: If latency exceeds budget by 40% across 15 frames, increase study stride
        if len(self._recent_latencies) >= 15:
            avg_latency = sum(self._recent_latencies[-15:]) / 15.0
            if avg_latency > self.current_tier.max_frame_latency_ms:
                # Heavy load: throttle StudyGuard inference frequency
                if self._dynamic_study_stride < 6:
                    self._dynamic_study_stride += 1
            elif avg_latency < self.current_tier.max_frame_latency_ms * 0.7:
                # Low load: restore default tier stride
                if self._dynamic_study_stride > self.current_tier.study_inference_stride:
                    self._dynamic_study_stride -= 1

    def record_dropped_frame(self) -> None:
        self._dropped_frames_count += 1

    @property
    def dropped_frames(self) -> int:
        return self._dropped_frames_count

    @property
    def average_latency_ms(self) -> float:
        if not self._recent_latencies:
            return 0.0
        return sum(self._recent_latencies) / len(self._recent_latencies)
