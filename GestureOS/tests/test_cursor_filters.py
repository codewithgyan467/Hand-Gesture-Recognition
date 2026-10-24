"""Unit tests for cursor smoothing filters and velocity limiting."""

import math
import pytest
from app.cursor.filters import OneEuroFilter2D, ExponentialMovingAverage2D, KalmanFilter2D
from app.cursor.cursor_engine import CursorEngine
from app.core.config import CursorConfig, ActiveRegionConfig
from app.core.types import Point2D


def test_one_euro_filter_jitter_reduction():
    # Low-speed jitter should be smoothed
    filt = OneEuroFilter2D(min_cutoff=1.0, beta=0.007)
    t = 1.0
    # Jittering around (100, 100)
    samples = [100.0, 100.8, 99.4, 100.5, 99.7, 100.2]
    filtered_vals = []
    for s in samples:
        fx, fy = filt.filter(s, s, timestamp=t)
        filtered_vals.append(fx)
        t += 0.033

    # Variance of filtered output should be lower than raw jitter
    raw_var = sum((x - 100.0) ** 2 for x in samples) / len(samples)
    filt_var = sum((x - 100.0) ** 2 for x in filtered_vals) / len(filtered_vals)
    assert filt_var < raw_var


def test_cursor_engine_dead_zone():
    engine = CursorEngine()
    t = 1.0
    pt1 = Point2D(0.500, 0.500)
    screen1 = engine.map_hand_to_screen(pt1, t)

    # Micro movement within dead zone (< 0.003 normalized)
    t += 0.033
    pt2 = Point2D(0.501, 0.501)
    screen2 = engine.map_hand_to_screen(pt2, t)

    # Position should not have shifted due to micro tremor
    assert screen1 == screen2


def test_cursor_engine_velocity_limit():
    cfg = CursorConfig(velocity_limit=50.0) # Maximum jump per frame
    engine = CursorEngine(cursor_config=cfg)

    # Start at center
    t = 1.0
    s1_x, s1_y = engine.map_hand_to_screen(Point2D(0.5, 0.5), t)

    # Sudden huge glitch to top-left (0.05, 0.05)
    t += 0.016 # 60 fps
    s2_x, s2_y = engine.map_hand_to_screen(Point2D(0.05, 0.05), t)

    jump = math.hypot(s2_x - s1_x, s2_y - s1_y)
    # Jump must be clamped by velocity limiter
    assert jump <= 70.0
