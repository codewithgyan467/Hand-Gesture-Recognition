"""System tray icon and background control menu for GestureOS."""

from __future__ import annotations
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QActionGroup
from PySide6.QtCore import Qt
from typing import Dict

from app.core.types import InteractionMode


def create_tray_icon_pixmap(color_hex: str = "#00e676") -> QPixmap:
    """Generates a stylish circular tray icon dynamically."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return pixmap


class GestureOSTrayIcon(QSystemTrayIcon):
    """System tray driver enabling background operation and status menu."""

    def __init__(self, main_window, parent=None) -> None:
        self._pixmap_active = create_tray_icon_pixmap("#00e676")
        self._pixmap_paused = create_tray_icon_pixmap("#f59e0b")
        self._pixmap_emergency = create_tray_icon_pixmap("#ef4444")

        super().__init__(QIcon(self._pixmap_active), parent)
        self.main_window = main_window
        self.setToolTip("GestureOS — AI Touchless Interface (Active)")

        self._menu = QMenu()
        self._mode_actions: Dict[str, QAction] = {}
        self._profile_actions: Dict[str, QAction] = {}
        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        self._menu.setStyleSheet(
            "QMenu { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', Arial, sans-serif; "
            "background-color: #2b3035; color: #dee2e6; border: 1px solid #495057; border-radius: 6px; padding: 4px; font-size: 13px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #0d6efd; color: #ffffff; }"
            "QMenu::separator { height: 1px; background: #495057; margin: 4px 8px; }"
        )

        title_action = self._menu.addAction("✨ GestureOS — Touchless AI")
        title_action.setEnabled(False)
        self._menu.addSeparator()

        self.action_show = self._menu.addAction("🖥 Open Dashboard")
        self.action_show.triggered.connect(self.main_window.show_and_raise)

        self._menu.addSeparator()

        # Arm / Disarm
        self.action_toggle_control = self._menu.addAction("⏸ Pause Mouse Control")
        self.action_toggle_control.triggered.connect(self.main_window.toggle_active_control)

        self.action_emergency_stop = self._menu.addAction("🛑 Emergency Stop (ESC)")
        self.action_emergency_stop.triggered.connect(self.main_window.trigger_emergency_stop)

        self._menu.addSeparator()

        # Interaction Mode Submenu
        self.menu_modes = self._menu.addMenu("🎮 Interaction Mode")
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        mode_options = [
            (InteractionMode.MOUSE, "Mouse (Cursor & Clicks)"),
            (InteractionMode.MEDIA, "Media (Audio & Playback)"),
            (InteractionMode.BROWSER, "Browser (Navigation & Tabs)"),
            (InteractionMode.PRESENTATION, "Presentation (Slide Deck)"),
            (InteractionMode.WINDOW, "Window Control (Task Manager)"),
            (InteractionMode.DRAWING, "Drawing (Air Canvas)"),
        ]
        for mode_val, mode_label in mode_options:
            act = self.menu_modes.addAction(mode_label)
            act.setCheckable(True)
            mode_group.addAction(act)
            self._mode_actions[mode_val.value] = act
            act.triggered.connect(lambda checked, m=mode_val: self.main_window.set_interaction_mode(m))

        # Profiles Submenu
        self.menu_profiles = self._menu.addMenu("⚙ Profiles")
        prof_group = QActionGroup(self)
        prof_group.setExclusive(True)

        profiles = ["Default", "Media", "Gaming", "Presentation", "Accessibility"]
        for p in profiles:
            act = self.menu_profiles.addAction(p)
            act.setCheckable(True)
            prof_group.addAction(act)
            self._profile_actions[p.lower()] = act
            act.triggered.connect(lambda checked, name=p: self.main_window.switch_profile(name))

        self._menu.addSeparator()

        # Setup & Configuration Tools
        self.action_wizard = self._menu.addAction("🧙 First-Launch Setup Wizard")
        self.action_wizard.triggered.connect(self.main_window.open_onboarding_wizard)

        self.action_calib = self._menu.addAction("🎯 Calibration Wizard")
        self.action_calib.triggered.connect(self.main_window.open_calibration_wizard)

        self.action_mappings = self._menu.addAction("🎛 Gesture Mappings & Settings")
        self.action_mappings.triggered.connect(self.main_window.open_gesture_editor)

        self.action_diag = self._menu.addAction("📊 Diagnostics & Telemetry")
        self.action_diag.triggered.connect(self.main_window.open_diagnostics)

        self._menu.addSeparator()

        self.action_restart_cam = self._menu.addAction("🔄 Restart Camera")
        self.action_restart_cam.triggered.connect(self.main_window.restart_camera)

        self.action_exit = self._menu.addAction("❌ Exit GestureOS")
        self.action_exit.triggered.connect(self.main_window.quit_application)

    def update_tray_state(
        self,
        is_active: bool,
        is_emergency: bool,
        current_mode: str,
        current_profile: str,
    ) -> None:
        """Synchronizes tray menu checkmarks and icons with live engine state."""
        if is_emergency:
            self.setIcon(QIcon(self._pixmap_emergency))
            self.setToolTip("GestureOS [EMERGENCY STOPPED]")
            self.action_toggle_control.setText("Reset Emergency Stop")
        elif is_active:
            self.setIcon(QIcon(self._pixmap_active))
            self.setToolTip(f"GestureOS [Active - {current_mode.capitalize()} Mode]")
            self.action_toggle_control.setText("Pause Mouse Control")
        else:
            self.setIcon(QIcon(self._pixmap_paused))
            self.setToolTip("GestureOS [Paused]")
            self.action_toggle_control.setText("Resume Mouse Control")

        # Update mode checkmarks
        for m_key, act in self._mode_actions.items():
            act.setChecked(m_key == current_mode)

        # Update profile checkmarks
        cur_prof_lower = current_profile.lower()
        for p_key, act in self._profile_actions.items():
            act.setChecked(p_key == cur_prof_lower)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.main_window.show_and_raise()
