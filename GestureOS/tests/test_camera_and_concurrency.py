"""Tests for camera bounded queue, stale frame dropping, and clean shutdown without thread leaks."""

import time
import numpy as np
import pytest
from app.camera.cv_camera import OpenCVCamera
from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine


def test_camera_bounded_queue_and_stale_frame_dropping():
    # Test bounded zero-latency logic on OpenCVCamera
    cam = OpenCVCamera(camera_index=0, width=640, height=480, fps=30)
    assert cam.is_bounded

    # Simulate pushing two frames: second frame must overwrite stale frame
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2 = np.ones((480, 640, 3), dtype=np.uint8)

    with cam._lock:
        cam._latest_frame = frame1
        cam._new_frame_event.set()

    # Second frame arrives before first is read: stale frame1 dropped
    cam._is_running = True
    with cam._lock:
        cam._latest_frame = frame2
        cam._new_frame_event.set()

    ret, freshest = cam.read_frame()
    assert ret
    assert np.array_equal(freshest, frame2)


def test_engine_clean_shutdown_no_zombie_threads():
    config = GestureOSConfig()
    config.camera.simulation_mode = True
    engine = GestureOSEngine(config=config, use_mock_controller=True)

    # Start engine
    started = engine.start()
    assert started
    assert engine._is_running
    assert engine._worker_thread is not None
    assert engine._worker_thread.is_alive()

    # Step at least once
    out = engine.step()
    assert out is not None

    # Stop engine
    engine.stop()
    assert not engine._is_running

    # Verify worker thread terminated cleanly
    time.sleep(0.1)
    assert not engine._worker_thread.is_alive()
