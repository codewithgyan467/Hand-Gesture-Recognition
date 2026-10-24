"""End-to-End Simulation Mode Integration Test."""

import pytest
from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.core.types import GestureState


def test_simulation_pipeline_execution():
    cfg = GestureOSConfig()
    cfg.camera.simulation_mode = True

    engine = GestureOSEngine(config=cfg, use_mock_controller=True)

    # Step through 15 simulated frames
    for _ in range(15):
        output = engine.step()
        assert output is not None
        assert output.annotated_frame is not None
        assert output.raw_frame.shape == (480, 640, 3)
        assert output.fps >= 0.0

    # Verify telemetry snapshot
    snap = engine.telemetry.get_snapshot()
    assert snap.uptime_sec >= 0.0
    assert snap.ram_mb > 0.0

    engine.stop()
