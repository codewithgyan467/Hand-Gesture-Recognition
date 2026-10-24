"""Dedicated Cursor Engine with active region mapping, smoothing, dead zone, and velocity limiting."""

from __future__ import annotations
import math
import time
from typing import Tuple, Optional
from app.core.config import CursorConfig, ActiveRegionConfig
from app.cursor.filters import OneEuroFilter2D, ExponentialMovingAverage2D, KalmanFilter2D
from app.vision.normalizer import LandmarkNormalizer
from app.core.types import Point2D


class CursorEngine:
    """Calculates screen cursor coordinates from hand landmarks with jitter-free tracking."""

    def __init__(
        self,
        cursor_config: Optional[CursorConfig] = None,
        active_region: Optional[ActiveRegionConfig] = None,
    ) -> None:
        self.cursor_config = cursor_config or CursorConfig()
        self.active_region = active_region or ActiveRegionConfig()

        self._filter_type = self.cursor_config.smoothing_filter
        self._one_euro = OneEuroFilter2D(
            min_cutoff=self.cursor_config.min_cutoff,
            beta=self.cursor_config.beta,
            d_cutoff=self.cursor_config.d_cutoff,
        )
        self._ema = ExponentialMovingAverage2D(alpha=self.cursor_config.ema_alpha)
        self._kalman = KalmanFilter2D()

        self._last_raw_point: Optional[Point2D] = None
        self._last_screen_x: float = self.cursor_config.screen_width / 2.0
        self._last_screen_y: float = self.cursor_config.screen_height / 2.0
        self._last_timestamp: float = time.time()

        self._apply_smoothing_level(self.cursor_config.smoothing_level)

    def _apply_smoothing_level(self, level: str) -> None:
        lvl = level.lower()
        if lvl in ("low", "fast"):
            # FAST PRESET: Minimum latency, maximum responsiveness, lightweight jitter dampening
            self._one_euro.filter_x.min_cutoff = 2.4
            self._one_euro.filter_x.beta = 0.025
            self._one_euro.filter_y.min_cutoff = 2.4
            self._one_euro.filter_y.beta = 0.025
            self._ema.alpha = 0.65
            self.active_region.dead_zone_radius = 0.002
        elif lvl in ("high", "precise", "ultra"):
            # PRECISE PRESET: Maximum stability, strong tremor suppression, precision targeting
            self._one_euro.filter_x.min_cutoff = 0.5
            self._one_euro.filter_x.beta = 0.0025
            self._one_euro.filter_y.min_cutoff = 0.5
            self._one_euro.filter_y.beta = 0.0025
            self._ema.alpha = 0.18
            self.active_region.dead_zone_radius = 0.0055
        else:  # "medium", "balanced", default
            # BALANCED PRESET: Recommended default - natural ballistics with adaptive precision
            self._one_euro.filter_x.min_cutoff = 1.1
            self._one_euro.filter_x.beta = 0.009
            self._one_euro.filter_y.min_cutoff = 1.1
            self._one_euro.filter_y.beta = 0.009
            self._ema.alpha = 0.35
            self.active_region.dead_zone_radius = 0.0035

    def set_smoothing_level(self, level: str) -> None:
        self.cursor_config.smoothing_level = level
        self._apply_smoothing_level(level)

    @property
    def x_filter(self):
        return self._one_euro.filter_x

    @property
    def y_filter(self):
        return self._one_euro.filter_y

    @property
    def filter_config(self):
        return self.active_region

    def set_screen_size(self, width: int, height: int) -> None:
        self.cursor_config.screen_width = width
        self.cursor_config.screen_height = height

    def map_hand_to_screen(
        self,
        hand_point: Point2D,
        timestamp: Optional[float] = None,
    ) -> Tuple[int, int]:
        """Maps normalized hand coordinates to absolute smoothed screen pixel coordinates."""
        if timestamp is None:
            timestamp = time.time()

        # 1. Dead Zone Check
        if self._last_raw_point is not None:
            delta = math.hypot(hand_point.x - self._last_raw_point.x, hand_point.y - self._last_raw_point.y)
            if delta < self.active_region.dead_zone_radius:
                # Hand tremor within dead zone; keep previous smoothed position
                return (int(self._last_screen_x), int(self._last_screen_y))

        self._last_raw_point = hand_point

        # 2. Active Region Remapping
        norm_pt = LandmarkNormalizer.map_to_active_region(
            hand_point,
            x_min=self.active_region.x_min,
            y_min=self.active_region.y_min,
            x_max=self.active_region.x_max,
            y_max=self.active_region.y_max,
        )

        # 3. Target raw pixel coordinates
        effective_x = (1.0 - norm_pt.x) if self.cursor_config.invert_x else norm_pt.x
        raw_x = effective_x * self.cursor_config.screen_width
        raw_y = norm_pt.y * self.cursor_config.screen_height

        # 4. Smoothing Filter Application
        filt = self.cursor_config.smoothing_filter.lower()
        if filt == "one_euro":
            smooth_x, smooth_y = self._one_euro.filter(raw_x, raw_y, timestamp)
        elif filt == "ema":
            smooth_x, smooth_y = self._ema.filter(raw_x, raw_y)
        elif filt == "kalman":
            smooth_x, smooth_y = self._kalman.filter(raw_x, raw_y)
        else:
            smooth_x, smooth_y = raw_x, raw_y

        # 5. Non-linear acceleration & Velocity Limiter
        dt = max(1e-4, timestamp - self._last_timestamp)
        jump_dist = math.hypot(smooth_x - self._last_screen_x, smooth_y - self._last_screen_y)

        # Check velocity limit
        max_jump = self.cursor_config.velocity_limit * (dt * 60.0) # Scaled to frame rate
        if jump_dist > max_jump and jump_dist > 50.0:
            scale = max_jump / jump_dist
            smooth_x = self._last_screen_x + (smooth_x - self._last_screen_x) * scale
            smooth_y = self._last_screen_y + (smooth_y - self._last_screen_y) * scale

        # Clamp to screen dimensions
        final_x = max(0, min(self.cursor_config.screen_width - 1, int(round(smooth_x))))
        final_y = max(0, min(self.cursor_config.screen_height - 1, int(round(smooth_y))))

        self._last_screen_x = smooth_x
        self._last_screen_y = smooth_y
        self._last_timestamp = timestamp

        return (final_x, final_y)

    def reset(self) -> None:
        self._one_euro.reset()
        self._ema.reset()
        self._kalman.reset()
        self._last_raw_point = None
