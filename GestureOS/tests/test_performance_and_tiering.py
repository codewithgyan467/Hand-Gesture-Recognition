"""Tests for hardware adaptation, performance tier profiles, and adaptive multi-rate decimation."""

import pytest
from app.diagnostics.hardware import HardwareProfiler, detect_hardware_profile
from app.core.performance import PerformanceController, TIER_PROFILES
from app.vision.model_manager import ModelManager


def test_hardware_profiler_and_tier_assignment():
    hw = HardwareProfiler.detect()
    assert hw.assigned_tier in ("FULL", "BALANCED", "LIGHT", "COMPATIBILITY")
    assert hw.cpu_cores_logical >= 1
    assert hw.ram_total_gb > 0.5


def test_performance_controller_adaptive_decimation():
    perf = PerformanceController(tier="BALANCED")
    assert perf.current_tier.study_inference_stride == 3

    # On consecutive high latency, dynamic stride increases to preserve frame rate
    for _ in range(20):
        perf.record_frame_latency(95.0)

    assert perf._dynamic_study_stride > perf.current_tier.study_inference_stride


def test_model_manager_lazy_study_guard_loading():
    mgr = ModelManager()
    # StudyGuard models should NOT be loaded initially
    assert not mgr.is_study_detector_loaded

    # Load on demand
    detector = mgr.get_or_load_study_detector()
    assert detector is not None
    assert mgr.is_study_detector_loaded

    # Unload on demand (release memory)
    mgr.unload_study_detector()
    assert not mgr.is_study_detector_loaded
