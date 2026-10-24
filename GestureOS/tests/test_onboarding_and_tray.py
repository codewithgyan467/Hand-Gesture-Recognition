"""Tests for Onboarding Wizard and System Tray synchronization."""

import pytest
import os
from PySide6.QtWidgets import QApplication
from app.core.config import GestureOSConfig
from app.ui.onboarding_wizard import OnboardingWizardDialog
from app.ui.system_tray import GestureOSTrayIcon


@pytest.fixture(scope="module")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_onboarding_wizard_navigation(qapp):
    class MockEngine:
        def __init__(self):
            self.config = GestureOSConfig()

    wizard = OnboardingWizardDialog(MockEngine())
    assert wizard.stack.currentIndex() == 0
    assert "Camera Setup" in wizard.lbl_step.text()

    # Navigate forward through all 6 pages
    for expected_page in range(1, 6):
        wizard._next_step()
        assert wizard.stack.currentIndex() == expected_page

    assert "Finish" in wizard.btn_next.text()

    # Navigate backward
    wizard._prev_step()
    assert wizard.stack.currentIndex() == 4

    wizard.close()
    wizard.deleteLater()
    qapp.processEvents()


def test_tray_icon_state_synchronization(qapp):
    class MockMainWindow:
        def show_and_raise(self): pass
        def toggle_active_control(self): pass
        def trigger_emergency_stop(self): pass
        def set_interaction_mode(self, m): pass
        def switch_profile(self, p): pass
        def open_onboarding_wizard(self): pass
        def open_calibration_wizard(self): pass
        def open_gesture_editor(self): pass
        def open_diagnostics(self): pass
        def restart_camera(self): pass
        def quit_application(self): pass

    mock_win = MockMainWindow()
    tray = GestureOSTrayIcon(mock_win)

    # 1. Active state
    tray.update_tray_state(
        is_active=True,
        is_emergency=False,
        current_mode="mouse",
        current_profile="default",
    )
    assert "[Active - Mouse Mode]" in tray.toolTip()
    assert "Pause" in tray.action_toggle_control.text()

    # 2. Paused state
    tray.update_tray_state(
        is_active=False,
        is_emergency=False,
        current_mode="media",
        current_profile="media",
    )
    assert "[Paused]" in tray.toolTip()
    assert "Resume" in tray.action_toggle_control.text()

    # 3. Emergency stopped state
    tray.update_tray_state(
        is_active=False,
        is_emergency=True,
        current_mode="mouse",
        current_profile="default",
    )
    assert "[EMERGENCY STOPPED]" in tray.toolTip()
    assert "Reset" in tray.action_toggle_control.text()

    tray.hide()
    tray.deleteLater()
    qapp.processEvents()
