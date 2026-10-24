"""Tests verifying the unified single window integration for GestureOS and StudyGuard."""

import os
import sys
import pytest
import numpy as np

# PySide6 offscreen testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.ui.main_window import GestureOSMainWindow
from app.vision.study_state_machine import StudyState


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_unified_window_study_guard_toggle(qapp):
    config = GestureOSConfig()
    config.camera.simulation_mode = True
    config.enable_study_guard = False

    engine = GestureOSEngine(config=config, use_mock_controller=True)
    window = GestureOSMainWindow(engine)

    # Verify initial state: Study Guard OFF
    assert not engine.enable_study_guard
    assert window.btn_study_switch.text() == "🎯 Study Guard: OFF"
    assert not window.btn_study_switch.isChecked()
    assert window.lbl_study_status.text() == "Status: Switched OFF"

    # Toggle switch ON via header button
    window.btn_study_switch.setChecked(True)
    window._on_study_guard_toggled(True)

    assert engine.enable_study_guard is True
    assert window.btn_study_switch.text() == "🎯 Study Guard: ON"
    assert window.btn_panel_study_toggle.text() == "Turn OFF"

    # Toggle switch OFF via panel button
    window._toggle_study_guard_from_panel()
    assert engine.enable_study_guard is False
    assert window.btn_study_switch.text() == "🎯 Study Guard: OFF"
    assert window.btn_panel_study_toggle.text() == "Turn ON"

    # Test hotkey simulation auto-enables Study Guard if OFF
    window._trigger_sim_book()
    assert engine.enable_study_guard is True
    assert engine.study_state_machine.current_state == StudyState.READING_BOOK

    # Test mute toggle
    initial_mute = engine.study_audio_player.muted
    window._toggle_study_mute()
    assert engine.study_audio_player.muted != initial_mute

    window._refresh_timer.stop()
    window.close()
    engine.stop()


def test_unified_window_ui_tick_sync(qapp):
    config = GestureOSConfig()
    config.camera.simulation_mode = True
    config.enable_study_guard = True

    engine = GestureOSEngine(config=config, use_mock_controller=True)
    window = GestureOSMainWindow(engine)

    # Step engine frame
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    output = engine.step(dummy_frame)

    assert output is not None
    assert output.study_active is True

    # Run tick
    window._on_ui_tick()
    assert "Status:" in window.lbl_study_status.text()

    window._refresh_timer.stop()
    window.close()
    engine.stop()
