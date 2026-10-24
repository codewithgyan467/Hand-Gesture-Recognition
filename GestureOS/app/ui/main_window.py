"""GestureOS Simplified Touchless Mouse Dashboard built with PySide6."""

from __future__ import annotations
import sys
import os
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QApplication,
    QFrame,
    QSystemTrayIcon,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from app.core.config import GestureOSConfig
from app.core.types import InteractionMode, GestureState
from app.core.engine import GestureOSEngine
from app.calibration.profile_manager import ProfileManager
from app.ui.camera_widget import CameraWidget
from app.ui.system_tray import GestureOSTrayIcon


BOOTSTRAP_DARK_THEME = """
QMainWindow {
    background-color: #212529;
    color: #dee2e6;
}
QDialog {
    background-color: #212529;
    color: #dee2e6;
}
QWidget {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", "Liberation Sans", Arial, sans-serif;
    color: #dee2e6;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #373b3e;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 16px;
    background-color: #2b3035;
    font-weight: 600;
    color: #f8f9fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #0d6efd;
    background-color: #2b3035;
    border-radius: 4px;
}
QPushButton {
    background-color: #343a40;
    color: #ffffff;
    border: 1px solid #495057;
    padding: 7px 14px;
    border-radius: 6px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #3d434a;
    border-color: #6c757d;
}
QPushButton:pressed {
    background-color: #2b3035;
}
QPushButton:checked {
    background-color: #0d6efd;
    border-color: #0d6efd;
    color: #ffffff;
}
QCheckBox {
    spacing: 8px;
    color: #dee2e6;
    font-weight: 400;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #6c757d;
    background-color: #212529;
}
QCheckBox::indicator:checked {
    background-color: #0d6efd;
    border-color: #0d6efd;
}
QSpinBox {
    background-color: #212529;
    border: 1px solid #495057;
    padding: 4px 10px;
    border-radius: 6px;
    color: #dee2e6;
    font-weight: 400;
}
QSpinBox:focus {
    border-color: #86b7fe;
}
QComboBox {
    background-color: #212529;
    border: 1px solid #495057;
    padding: 5px 12px;
    border-radius: 6px;
    color: #dee2e6;
    font-weight: 400;
}
QComboBox:focus {
    border-color: #86b7fe;
}
QComboBox::drop-down {
    border: none;
}
QMenu {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", Arial, sans-serif;
    background-color: #2b3035;
    color: #dee2e6;
    border: 1px solid #495057;
    border-radius: 6px;
    padding: 4px;
    font-size: 13px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #0d6efd;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #495057;
    margin: 4px 8px;
}
QTableWidget {
    background-color: #212529;
    border: 1px solid #373b3e;
    gridline-color: #373b3e;
}
QHeaderView::section {
    background-color: #2b3035;
    color: #dee2e6;
    border: none;
    border-bottom: 2px solid #495057;
    padding: 6px;
    font-weight: 600;
}
QTableWidget::item {
    padding: 5px;
    color: #dee2e6;
}
"""
CLEAN_DARK_THEME = BOOTSTRAP_DARK_THEME



class GestureOSMainWindow(QMainWindow):
    """Simplified, elegant, distraction-free touchless mouse dashboard."""

    def __init__(self, engine: GestureOSEngine) -> None:
        super().__init__()
        self.engine = engine
        self.profile_manager = ProfileManager()

        self.setWindowTitle("GestureOS — AI Touchless Mouse")
        self.resize(1140, 720)
        self.setMinimumSize(920, 580)
        self.setStyleSheet(CLEAN_DARK_THEME)

        self._init_ui()
        self._init_system_tray()
        self._init_shortcuts()

        # UI refresh timer (30 Hz)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_ui_tick)
        self._refresh_timer.start(33)

        # Start directly in ACTIVE mode so hand immediately controls the mouse
        self.engine.state_machine.transition_to(
            GestureState.ACTIVE, "Dashboard launched - touchless mouse active"
        )

    def _init_shortcuts(self) -> None:
        self.shortcut_toggle = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.shortcut_toggle.activated.connect(self.toggle_active_control)

        # Hotkeys for StudyGuard simulation & meme audio triggers
        self.shortcut_book = QShortcut(QKeySequence("B"), self)
        self.shortcut_book.activated.connect(self._trigger_sim_book)

        self.shortcut_close = QShortcut(QKeySequence("C"), self)
        self.shortcut_close.activated.connect(self._trigger_sim_close_book)

        self.shortcut_phone = QShortcut(QKeySequence("P"), self)
        self.shortcut_phone.activated.connect(self._trigger_sim_phone)

        self.shortcut_water = QShortcut(QKeySequence("W"), self)
        self.shortcut_water.activated.connect(self._trigger_sim_water)

        self.shortcut_mute = QShortcut(QKeySequence("M"), self)
        self.shortcut_mute.activated.connect(self._toggle_study_mute)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Header Bar
        header = QHBoxLayout()
        header.setSpacing(14)

        # Brand Title
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_brand = QLabel("GestureOS")
        lbl_brand.setStyleSheet("font-size: 18px; font-weight: 700; color: #f8f9fa;")
        lbl_subtitle = QLabel("Touchless PC & Laptop Interface")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #adb5bd;")
        title_box.addWidget(lbl_brand)
        title_box.addWidget(lbl_subtitle)
        header.addLayout(title_box)

        header.addSpacing(16)

        # Status Badge (.badge .bg-success)
        self.lbl_status = QLabel("● Touchless Mouse: Active")
        self.lbl_status.setStyleSheet(
            "background-color: #198754; color: #ffffff; "
            "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
        )
        header.addWidget(self.lbl_status)

        # Detected Gesture Badge (.badge .bg-dark .border)
        self.lbl_gesture = QLabel("Hand: Ready")
        self.lbl_gesture.setStyleSheet(
            "background-color: #343a40; color: #dee2e6; border: 1px solid #495057; "
            "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
        )
        header.addWidget(self.lbl_gesture)

        # Dispatched Action Badge (.badge .bg-dark .border)
        self.lbl_action = QLabel("Action: Ready")
        self.lbl_action.setStyleSheet(
            "background-color: #343a40; color: #adb5bd; border: 1px solid #495057; "
            "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
        )
        header.addWidget(self.lbl_action)

        header.addStretch()

        # Simple Mode Toggle
        self.chk_simple_mode = QCheckBox("Simple Mode")
        self.chk_simple_mode.setChecked(getattr(self.engine.config, "simple_mode", True))
        self.chk_simple_mode.toggled.connect(self._on_simple_mode_toggled)
        self.chk_simple_mode.setToolTip("Prioritize intuitive 7-gesture vocabulary across all modes")
        header.addWidget(self.chk_simple_mode)

        header.addSpacing(10)

        # StudyGuard AI Meme Monitor ON/OFF Switch
        self.btn_study_switch = QPushButton("🎯 Study Guard: OFF")
        self.btn_study_switch.setCheckable(True)
        self.btn_study_switch.setChecked(self.engine.enable_study_guard)
        self._update_study_switch_style(self.engine.enable_study_guard)
        self.btn_study_switch.clicked.connect(self._on_study_guard_toggled)
        self.btn_study_switch.setToolTip("Toggle Study Guard AI Meme Detector (Book Close, Phone Distraction, Hydration)")
        header.addWidget(self.btn_study_switch)

        header.addSpacing(10)

        # Pause / Resume Button (.btn-secondary)
        self.btn_toggle = QPushButton("⏸ Pause Mouse (Ctrl+Space)")
        self.btn_toggle.setStyleSheet(
            "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; font-weight: 500; padding: 6px 14px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #3d434a; border-color: #6c757d; }"
        )
        self.btn_toggle.clicked.connect(self.toggle_active_control)
        header.addWidget(self.btn_toggle)

        # Emergency Stop Button (.btn-danger)
        self.btn_emergency = QPushButton("🛑 Stop (ESC)")
        self.btn_emergency.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: #ffffff; border: 1px solid #dc3545; font-weight: 500; padding: 6px 14px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #bb2d3b; border-color: #b02a37; }"
        )
        self.btn_emergency.clicked.connect(self.trigger_emergency_stop)
        header.addWidget(self.btn_emergency)

        main_layout.addLayout(header)

        # 2. Body: Left = Camera Feed, Right = Clean Controls
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # Left Column: Camera View
        cam_col = QVBoxLayout()
        cam_col.setSpacing(8)

        self.camera_widget = CameraWidget()
        cam_col.addWidget(self.camera_widget, 1)

        # Bottom Camera Controls Row
        cam_bar = QHBoxLayout()
        cam_bar.setSpacing(16)

        self.chk_overlay = QCheckBox("Show Tracking & Target Box")
        self.chk_overlay.setChecked(self.engine.config.show_debug_overlay)
        self.chk_overlay.toggled.connect(self._on_overlay_toggled)
        cam_bar.addWidget(self.chk_overlay)

        self.chk_mirror = QCheckBox("Mirror Camera")
        self.chk_mirror.setChecked(self.engine.config.camera.mirror)
        self.chk_mirror.toggled.connect(self._on_mirror_toggled)
        cam_bar.addWidget(self.chk_mirror)

        self.chk_invert_x = QCheckBox("Invert Horizontal (Mirror Fix)")
        self.chk_invert_x.setChecked(self.engine.cursor_engine.cursor_config.invert_x)
        self.chk_invert_x.toggled.connect(self._on_invert_x_toggled)
        cam_bar.addWidget(self.chk_invert_x)

        cam_bar.addStretch()

        lbl_cam_idx = QLabel("Camera:")
        lbl_cam_idx.setStyleSheet("color: #adb5bd; font-size: 12px;")
        cam_bar.addWidget(lbl_cam_idx)

        self.spin_cam = QSpinBox()
        self.spin_cam.setRange(0, 6)
        self.spin_cam.setValue(self.engine.config.camera.camera_index)
        self.spin_cam.valueChanged.connect(self._on_camera_index_changed)
        cam_bar.addWidget(self.spin_cam)

        self.lbl_fps = QLabel("30.0 FPS")
        self.lbl_fps.setStyleSheet("color: #adb5bd; font-weight: 600; font-size: 12px;")
        cam_bar.addWidget(self.lbl_fps)

        cam_col.addLayout(cam_bar)
        body_layout.addLayout(cam_col, 65)

        # Right Column: Clean Control Cards
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # Card 1: Dynamic Gesture Controls Guide
        self.guide_box = QGroupBox("Gesture Controls")
        self.guide_vbox = QVBoxLayout(self.guide_box)
        self.guide_vbox.setSpacing(10)
        self.guide_vbox.setContentsMargins(14, 18, 14, 14)
        self._update_gesture_guide()

        right_col.addWidget(self.guide_box)

        # Card 2: Pointer Speed & Smoothing Presets
        speed_box = QGroupBox("Pointer Smoothing Preset")
        speed_vbox = QVBoxLayout(speed_box)
        speed_vbox.setSpacing(8)
        speed_vbox.setContentsMargins(14, 18, 14, 14)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)

        self.btn_fast = QPushButton("Fast")
        self.btn_fast.setToolTip("Minimum latency and maximum cursor responsiveness")
        self.btn_smooth = QPushButton("Balanced (Default)")
        self.btn_smooth.setToolTip("Recommended default: natural ballistics and tremor filtering")
        self.btn_ultra = QPushButton("Precise")
        self.btn_ultra.setToolTip("Maximum stability: rock-steady cursor for fine clicking")

        for b in [self.btn_fast, self.btn_smooth, self.btn_ultra]:
            b.setCheckable(True)
            b.setStyleSheet(
                "QPushButton { background-color: #212529; border: 1px solid #495057; padding: 6px 12px; font-size: 12px; border-radius: 6px; color: #dee2e6; font-weight: 500; }"
                "QPushButton:hover { background-color: #2b3035; border-color: #6c757d; color: #ffffff; }"
                "QPushButton:checked { background-color: #0d6efd; border-color: #0d6efd; color: #ffffff; font-weight: 600; }"
            )

        self.btn_smooth.setChecked(True)

        self.btn_fast.clicked.connect(lambda: self._set_smoothing("fast"))
        self.btn_smooth.clicked.connect(lambda: self._set_smoothing("balanced"))
        self.btn_ultra.clicked.connect(lambda: self._set_smoothing("precise"))

        speed_row.addWidget(self.btn_fast)
        speed_row.addWidget(self.btn_smooth)
        speed_row.addWidget(self.btn_ultra)
        speed_vbox.addLayout(speed_row)

        right_col.addWidget(speed_box)

        # Card 3: Study Guard AI Meme Distraction & Hydration Monitor
        study_box = QGroupBox("Study Guard — AI Meme Monitor")
        study_vbox = QVBoxLayout(study_box)
        study_vbox.setSpacing(8)
        study_vbox.setContentsMargins(14, 16, 14, 14)

        # Status and Panel Toggle row
        st_hdr = QHBoxLayout()
        st_hdr.setSpacing(10)
        self.lbl_study_status = QLabel("Status: Switched OFF")
        self.lbl_study_status.setStyleSheet("color: #adb5bd; font-size: 12px; font-weight: 500;")
        st_hdr.addWidget(self.lbl_study_status, 1)

        self.btn_panel_study_toggle = QPushButton("Turn ON")
        self.btn_panel_study_toggle.setCheckable(True)
        self.btn_panel_study_toggle.setChecked(self.engine.enable_study_guard)
        self.btn_panel_study_toggle.setStyleSheet(
            "QPushButton { background-color: #0dcaf0; color: #000000; border: none; font-weight: 600; font-size: 11px; padding: 4px 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #31d2f2; }"
        )
        self.btn_panel_study_toggle.clicked.connect(self._toggle_study_guard_from_panel)
        st_hdr.addWidget(self.btn_panel_study_toggle)
        study_vbox.addLayout(st_hdr)

        # Meme rules description
        rules_lbl = QLabel(
            "• <b>Close Book</b> ➜ <i>'Kyu nahi ho rahi padhai'</i><br>"
            "• <b>Phone After Book</b> ➜ <i>'Abeyy padhai likhai karo'</i><br>"
            "• <b>Drink Water</b> ➜ <i>'Pani pani'</i>"
        )
        rules_lbl.setStyleSheet("color: #ced4da; font-size: 11px; line-height: 135%;")
        rules_lbl.setTextFormat(Qt.RichText)
        study_vbox.addWidget(rules_lbl)

        # Simulation & test buttons row
        test_row = QHBoxLayout()
        test_row.setSpacing(6)

        btn_t_book = QPushButton("📖 Read (B)")
        btn_t_book.setToolTip("Simulate reading book")
        btn_t_book.setStyleSheet("QPushButton { font-size: 11px; padding: 4px 6px; }")
        btn_t_book.clicked.connect(self._trigger_sim_book)

        btn_t_close = QPushButton("📕 Close (C)")
        btn_t_close.setToolTip("Simulate closing book -> Kyu nahi ho rahi padhai")
        btn_t_close.setStyleSheet("QPushButton { font-size: 11px; padding: 4px 6px; }")
        btn_t_close.clicked.connect(self._trigger_sim_close_book)

        btn_t_phone = QPushButton("📱 Phone (P)")
        btn_t_phone.setToolTip("Simulate phone distraction -> Abeyy padhai likhai karo")
        btn_t_phone.setStyleSheet("QPushButton { font-size: 11px; padding: 4px 6px; }")
        btn_t_phone.clicked.connect(self._trigger_sim_phone)

        btn_t_water = QPushButton("💧 Water (W)")
        btn_t_water.setToolTip("Simulate drinking water -> Pani pani")
        btn_t_water.setStyleSheet("QPushButton { font-size: 11px; padding: 4px 6px; }")
        btn_t_water.clicked.connect(self._trigger_sim_water)

        test_row.addWidget(btn_t_book)
        test_row.addWidget(btn_t_close)
        test_row.addWidget(btn_t_phone)
        test_row.addWidget(btn_t_water)
        study_vbox.addLayout(test_row)

        # Audio mute button row
        self.btn_study_mute = QPushButton("🔊 Meme Audio: Active (Press M to Mute)")
        self.btn_study_mute.setStyleSheet("QPushButton { background-color: #212529; color: #ced4da; font-size: 11px; padding: 5px 8px; border: 1px solid #495057; }")
        self.btn_study_mute.clicked.connect(self._toggle_study_mute)
        study_vbox.addWidget(self.btn_study_mute)

        right_col.addWidget(study_box)

        # Card 3: Quick Status & Recovery Action
        action_box = QGroupBox("Quick Action")
        action_vbox = QVBoxLayout(action_box)
        action_vbox.setSpacing(10)
        action_vbox.setContentsMargins(14, 18, 14, 14)

        self.btn_rearm = QPushButton("↺ Re-arm / Recenter Mouse")
        self.btn_rearm.setStyleSheet(
            "QPushButton { background-color: #198754; color: #ffffff; border: 1px solid #198754; font-weight: 500; font-size: 13px; padding: 8px 14px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #157347; border-color: #146c43; }"
        )
        self.btn_rearm.clicked.connect(self._rearm_mouse)
        action_vbox.addWidget(self.btn_rearm)

        self.lbl_tip = QLabel("💡 <i>Move hand inside target box to reach screen corners easily.</i>")
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setStyleSheet("color: #adb5bd; font-size: 12px;")
        action_vbox.addWidget(self.lbl_tip)

        right_col.addWidget(action_box)
        right_col.addStretch()

        body_layout.addLayout(right_col, 35)
        main_layout.addLayout(body_layout)

        # 3. Bottom Utility & Tool Bar (Progressive Disclosure)
        footer = QHBoxLayout()
        footer.setSpacing(10)

        # Mode selector combo
        lbl_mode = QLabel("Mode:")
        lbl_mode.setStyleSheet("font-weight: 600; color: #adb5bd; font-size: 12px;")
        footer.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self._mode_list = [
            (InteractionMode.MOUSE, "Mouse (Default)"),
            (InteractionMode.MEDIA, "Media"),
            (InteractionMode.BROWSER, "Browser"),
            (InteractionMode.PRESENTATION, "Presentation"),
            (InteractionMode.WINDOW, "Window Control"),
            (InteractionMode.DRAWING, "Air Drawing"),
        ]
        for m_val, m_title in self._mode_list:
            self.combo_mode.addItem(m_title, m_val)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_combo_changed)
        footer.addWidget(self.combo_mode)

        # Profile selector combo
        lbl_prof = QLabel("Profile:")
        lbl_prof.setStyleSheet("font-weight: 600; color: #adb5bd; font-size: 12px;")
        footer.addWidget(lbl_prof)

        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["Default", "Media", "Gaming", "Presentation", "Accessibility"])
        self.combo_profile.currentTextChanged.connect(self.switch_profile)
        footer.addWidget(self.combo_profile)

        footer.addStretch()

        # Clean tool buttons
        btn_wizard = QPushButton("🧙 Setup Wizard")
        btn_wizard.clicked.connect(self.open_onboarding_wizard)
        footer.addWidget(btn_wizard)

        btn_calib = QPushButton("🎯 Calibration")
        btn_calib.clicked.connect(self.open_calibration_wizard)
        footer.addWidget(btn_calib)

        btn_mappings = QPushButton("🎛 Mappings")
        btn_mappings.clicked.connect(self.open_gesture_editor)
        footer.addWidget(btn_mappings)

        btn_canvas = QPushButton("🎨 Air Canvas")
        btn_canvas.clicked.connect(self.open_drawing_canvas)
        footer.addWidget(btn_canvas)

        btn_diag = QPushButton("📊 Diagnostics")
        btn_diag.clicked.connect(self.open_diagnostics)
        footer.addWidget(btn_diag)

        main_layout.addLayout(footer)

    def _init_system_tray(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = GestureOSTrayIcon(self, self)
            self.tray_icon.show()
        else:
            self.tray_icon = None

    def _set_smoothing(self, level: str) -> None:
        lvl = level.lower()
        self.btn_fast.setChecked(lvl in ("low", "fast"))
        self.btn_smooth.setChecked(lvl in ("medium", "balanced"))
        self.btn_ultra.setChecked(lvl in ("high", "precise", "ultra"))
        self.engine.cursor_engine._apply_smoothing_level(lvl)

    def _on_simple_mode_toggled(self, checked: bool) -> None:
        self.engine.config.simple_mode = checked
        self._update_gesture_guide()

    def _update_gesture_guide(self) -> None:
        if not hasattr(self, "guide_vbox") or self.guide_vbox is None:
            return

        while self.guide_vbox.count() > 0:
            item = self.guide_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count() > 0:
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        mode_name = self.engine.mode_manager.current_mode_name
        is_simple = getattr(self.engine.config, "simple_mode", True)
        title_suffix = " (Simple Vocabulary)" if is_simple else " (Advanced Vocabulary)"
        self.guide_box.setTitle(f"Gesture Controls — {mode_name} Mode{title_suffix}")

        if mode_name == "Media":
            controls = [
                ("🖐", "<b>Move Hand</b>", "Mode pointer control"),
                ("👍", "<b>Thumbs Up</b>", "Volume Up (+3% smooth step)"),
                ("👎", "<b>Thumbs Down</b>", "Volume Down (-3% smooth step)"),
                ("✌", "<b>Two Fingers (Peace)</b>", "Play / Pause toggle"),
                ("👉", "<b>Swipe Right</b>", "Next track"),
                ("👈", "<b>Swipe Left</b>", "Previous track"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]
        elif mode_name == "Browser":
            controls = [
                ("🖐", "<b>Move Hand</b>", "Position browser cursor"),
                ("✊", "<b>Right / Left Fist</b>", "Right fist: Back | Left fist: Forward"),
                ("👍", "<b>Thumbs Up</b>", "Smooth scroll page up"),
                ("👎", "<b>Thumbs Down</b>", "Smooth scroll page down"),
                ("✌", "<b>Two Fingers (Peace)</b>", "Open new browser tab"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]
        elif mode_name == "Presentation":
            controls = [
                ("🖐", "<b>Move Hand / Pointer</b>", "Virtual laser pointer"),
                ("👍", "<b>Thumbs Up</b>", "Start slideshow (F5)"),
                ("✊", "<b>Fist</b>", "Exit presentation (ESC)"),
                ("👉", "<b>Swipe Right</b>", "Next slide"),
                ("👈", "<b>Swipe Left</b>", "Previous slide"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]
        elif mode_name == "Window":
            controls = [
                ("🖐", "<b>Move Hand</b>", "Cursor control"),
                ("👉", "<b>Swipe Right</b>", "Next window (Alt+Tab)"),
                ("👈", "<b>Swipe Left</b>", "Previous window"),
                ("👍", "<b>Thumbs Up</b>", "Maximize active window"),
                ("👎", "<b>Thumbs Down</b>", "Minimize window"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]
        elif mode_name == "Drawing":
            controls = [
                ("🖐", "<b>Move Hand / Point</b>", "Draw stroke on air canvas"),
                ("🤏", "<b>Pinch Index</b>", "Select stroke / grab"),
                ("✌", "<b>Two Fingers (Peace)</b>", "Switch between brush & eraser"),
                ("✊", "<b>Fist</b>", "Pause drawing / lift pen"),
                ("👍", "<b>Thumbs Up</b>", "Undo last stroke"),
                ("👎", "<b>Thumbs Down</b>", "Redo stroke"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]
        else:  # Mouse Mode (Default)
            controls = [
                ("🖐", "<b>Move Hand</b>", "Guides the mouse cursor across screen"),
                ("✊", "<b>Right Hand Fist / Punch</b>", "Right click"),
                ("✊", "<b>Left Hand Fist / Punch</b>", "Left click"),
                ("🤏", "<b>Pinch Finger + Move</b>", "Pinch tap to click; pinch + move to drag"),
                ("👍", "<b>Thumbs Up</b>", "Smooth scroll vertical up"),
                ("👎", "<b>Thumbs Down</b>", "Smooth scroll vertical down"),
                ("✌", "<b>Two Fingers</b>", "Secondary action / alternate scroll"),
                ("🛑", "<b>Both Fists</b>", "Instant emergency stop"),
            ]

        for icon, title, desc in controls:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl_icon = QLabel(icon)
            lbl_icon.setStyleSheet("font-size: 18px;")
            lbl_icon.setFixedWidth(24)

            text_box = QVBoxLayout()
            text_box.setSpacing(1)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-size: 13px; color: #f8f9fa; font-weight: 600;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("font-size: 12px; color: #adb5bd;")
            text_box.addWidget(lbl_t)
            text_box.addWidget(lbl_d)

            row.addWidget(lbl_icon)
            row.addLayout(text_box)
            row.addStretch()
            self.guide_vbox.addLayout(row)

    def _rearm_mouse(self) -> None:
        if self.engine.state_machine.is_emergency_stopped:
            self.engine.state_machine.clear_emergency_stop(activate=True)
        else:
            self.engine.state_machine.transition_to(GestureState.ACTIVE, "User recentered mouse")
        self.engine.cursor_engine.reset()

    def _on_camera_index_changed(self, idx: int) -> None:
        if idx != self.engine.config.camera.camera_index:
            self.engine.config.camera.camera_index = idx
            self.engine.stop()
            self.engine.start()

    def _on_overlay_toggled(self, checked: bool) -> None:
        self.engine.config.show_debug_overlay = checked

    def _on_mirror_toggled(self, checked: bool) -> None:
        self.engine.config.camera.mirror = checked
        self.engine.camera.mirror = checked

    def _on_invert_x_toggled(self, checked: bool) -> None:
        self.engine.config.cursor.invert_x = checked
        self.engine.cursor_engine.cursor_config.invert_x = checked
        if hasattr(self.engine, "dynamic_detector"):
            self.engine.dynamic_detector.invert_x = checked

    def toggle_active_control(self) -> None:
        if self.engine.state_machine.is_emergency_stopped:
            self.engine.state_machine.clear_emergency_stop(activate=True)
        elif self.engine.state_machine.is_active:
            self.engine.state_machine.deactivate("User manual toggle to Passive Mode")
        else:
            self.engine.state_machine.transition_to(GestureState.ACTIVE, "User manual toggle to Active Control")

    def _update_study_switch_style(self, checked: bool) -> None:
        if checked:
            self.btn_study_switch.setText("🎯 Study Guard: ON")
            self.btn_study_switch.setStyleSheet(
                "QPushButton { background-color: #0dcaf0; color: #000000; border: 1px solid #0dcaf0; "
                "font-weight: 700; padding: 6px 14px; border-radius: 6px; font-size: 13px; }"
                "QPushButton:hover { background-color: #31d2f2; border-color: #25cff2; }"
            )
            if hasattr(self, "btn_panel_study_toggle"):
                self.btn_panel_study_toggle.setText("Turn OFF")
                self.btn_panel_study_toggle.setChecked(True)
                self.btn_panel_study_toggle.setStyleSheet(
                    "QPushButton { background-color: #dc3545; color: #ffffff; border: none; font-weight: 600; font-size: 11px; padding: 4px 10px; border-radius: 4px; }"
                    "QPushButton:hover { background-color: #bb2d3b; }"
                )
        else:
            self.btn_study_switch.setText("🎯 Study Guard: OFF")
            self.btn_study_switch.setStyleSheet(
                "QPushButton { background-color: #2b3035; color: #adb5bd; border: 1px solid #495057; "
                "font-weight: 600; padding: 6px 14px; border-radius: 6px; font-size: 13px; }"
                "QPushButton:hover { background-color: #343a40; border-color: #6c757d; color: #dee2e6; }"
            )
            if hasattr(self, "btn_panel_study_toggle"):
                self.btn_panel_study_toggle.setText("Turn ON")
                self.btn_panel_study_toggle.setChecked(False)
                self.btn_panel_study_toggle.setStyleSheet(
                    "QPushButton { background-color: #0dcaf0; color: #000000; border: none; font-weight: 600; font-size: 11px; padding: 4px 10px; border-radius: 4px; }"
                    "QPushButton:hover { background-color: #31d2f2; }"
                )

    def _on_study_guard_toggled(self, checked: bool) -> None:
        self.engine.set_study_guard_enabled(checked)
        self._update_study_switch_style(checked)

    def _toggle_study_guard_from_panel(self) -> None:
        new_state = not self.engine.enable_study_guard
        self.btn_study_switch.setChecked(new_state)
        self._on_study_guard_toggled(new_state)

    def _trigger_sim_book(self) -> None:
        if not self.engine.enable_study_guard:
            self.btn_study_switch.setChecked(True)
            self._on_study_guard_toggled(True)
        self.engine.study_state_machine.trigger_manual_book_read()

    def _trigger_sim_close_book(self) -> None:
        if not self.engine.enable_study_guard:
            self.btn_study_switch.setChecked(True)
            self._on_study_guard_toggled(True)
        self.engine.study_state_machine.trigger_manual_book_close()

    def _trigger_sim_phone(self) -> None:
        if not self.engine.enable_study_guard:
            self.btn_study_switch.setChecked(True)
            self._on_study_guard_toggled(True)
        self.engine.study_state_machine.trigger_manual_phone_distraction()

    def _trigger_sim_water(self) -> None:
        if not self.engine.enable_study_guard:
            self.btn_study_switch.setChecked(True)
            self._on_study_guard_toggled(True)
        self.engine.study_state_machine.trigger_manual_drinking()

    def _toggle_study_mute(self) -> None:
        is_muted = self.engine.study_audio_player.toggle_mute()
        if hasattr(self, "btn_study_mute"):
            self.btn_study_mute.setText(
                "🔇 Audio: Muted (Press M to Unmute)" if is_muted else "🔊 Meme Audio: Active (Press M to Mute)"
            )

    def trigger_emergency_stop(self) -> None:
        self.engine.emergency_guard.trigger("Emergency button pressed in UI")

    def _on_ui_tick(self) -> None:
        output = self.engine.latest_output
        if output is not None:
            # 1. Update Camera Widget
            self.camera_widget.update_frame(output.annotated_frame)

            # 2. Update FPS
            self.lbl_fps.setText(f"{output.fps:.1f} FPS")

            # 3. Update Status
            st = output.state.lower()
            if st == "emergency_stop":
                self.lbl_status.setText("🛑 Emergency Stopped")
                self.lbl_status.setStyleSheet(
                    "background-color: #dc3545; color: #ffffff; "
                    "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                )
                self.btn_toggle.setText("🔓 Reset Emergency (ESC)")
                self.btn_toggle.setStyleSheet(
                    "QPushButton { background-color: #dc3545; color: #ffffff; border: 1px solid #dc3545; font-weight: 500; padding: 6px 14px; border-radius: 6px; }"
                    "QPushButton:hover { background-color: #bb2d3b; }"
                )
            elif self.engine.state_machine.is_active:
                if st == "tracking_lost":
                    self.lbl_status.setText("● Ready: Waiting for Hand")
                    self.lbl_status.setStyleSheet(
                        "background-color: #0d6efd; color: #ffffff; "
                        "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                    )
                else:
                    self.lbl_status.setText("● Touchless Mouse: Active")
                    self.lbl_status.setStyleSheet(
                        "background-color: #198754; color: #ffffff; "
                        "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                    )
                self.btn_toggle.setText("⏸ Pause Mouse (Ctrl+Space)")
                self.btn_toggle.setStyleSheet(
                    "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; font-weight: 500; padding: 6px 14px; border-radius: 6px; }"
                    "QPushButton:hover { background-color: #3d434a; border-color: #6c757d; }"
                )
            else:
                self.lbl_status.setText("⏸ Mouse: Paused")
                self.lbl_status.setStyleSheet(
                    "background-color: #ffc107; color: #000000; "
                    "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                )
                self.btn_toggle.setText("▶ Resume Mouse (Ctrl+Space)")
                self.btn_toggle.setStyleSheet(
                    "QPushButton { background-color: #198754; color: #ffffff; border: 1px solid #198754; font-weight: 500; padding: 6px 14px; border-radius: 6px; }"
                    "QPushButton:hover { background-color: #157347; }"
                )

            # 4. Update Current Gesture
            if output.gesture != "none":
                self.lbl_gesture.setText(f"Hand: {output.gesture.capitalize()}")
            else:
                self.lbl_gesture.setText("Hand: Tracking")

            # 5. Update Dispatched Action Pill (Subtle immediate feedback)
            import time
            if output.dispatched_intent is not None:
                itype = output.dispatched_intent.intent_type.value.upper()
                action_map = {
                    "LEFT_CLICK": "✔ Left Click",
                    "RIGHT_CLICK": "✔ Right Click",
                    "DOUBLE_CLICK": "✔ Double Click",
                    "DRAG_START": "✊ Drag Start",
                    "DRAG_MOVE": "✊ Dragging",
                    "DRAG_END": "✋ Drag Release",
                    "SCROLL_VERTICAL": "▲ Scroll Up" if output.dispatched_intent.params.get("dy", 1) > 0 else "▼ Scroll Down",
                    "VOLUME_SET": f"🔊 Vol {output.dispatched_intent.params.get('level', 50)}%",
                    "MEDIA_PLAY_PAUSE": "⏯ Play / Pause",
                    "MEDIA_NEXT": "⏭ Next Track",
                    "MEDIA_PREV": "⏮ Prev Track",
                    "BROWSER_NEW_TAB": "🗂 New Tab",
                    "BROWSER_BACK": "⬅ Back",
                    "BROWSER_FORWARD": "➡ Forward",
                    "PRESENTATION_START": "▶ Start Slides",
                    "PRESENTATION_STOP": "⏹ Exit Slides",
                    "WINDOW_MAXIMIZE": "🗖 Maximize",
                    "WINDOW_MINIMIZE": "🗕 Minimize",
                    "DRAW_STROKE": "🎨 Draw",
                    "DRAW_UNDO": "↺ Undo",
                    "DRAW_REDO": "↻ Redo",
                }
                action_text = action_map.get(itype, itype)
                self.lbl_action.setText(f"Action: {action_text}")
                self.lbl_action.setStyleSheet(
                    "background-color: #0d6efd; color: #ffffff; "
                    "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                )
                self._last_action_time = time.time()
            elif hasattr(self, "_last_action_time") and time.time() - self._last_action_time > 0.6:
                self.lbl_action.setText("Action: Ready")
                self.lbl_action.setStyleSheet(
                    "background-color: #343a40; color: #adb5bd; border: 1px solid #495057; "
                    "padding: 5px 12px; border-radius: 4px; font-weight: 500; font-size: 12px;"
                )

            # 5b. Synchronize Study Guard State & Alert Banner in UI
            if hasattr(self, "lbl_study_status"):
                if getattr(output, "study_active", False):
                    st_val = getattr(output, "study_state", "IDLE")
                    alert = getattr(output, "study_alert", None)
                    if alert:
                        self.lbl_study_status.setText(f"🚨 {alert}")
                        self.lbl_study_status.setStyleSheet("color: #0dcaf0; font-weight: 700; font-size: 11px;")
                    else:
                        self.lbl_study_status.setText(f"Status: {st_val}")
                        self.lbl_study_status.setStyleSheet("color: #20c997; font-weight: 600; font-size: 11px;")
                else:
                    self.lbl_study_status.setText("Status: Switched OFF")
                    self.lbl_study_status.setStyleSheet("color: #adb5bd; font-size: 11px;")

            if hasattr(self, "btn_study_switch"):
                if self.btn_study_switch.isChecked() != self.engine.enable_study_guard:
                    self.btn_study_switch.blockSignals(True)
                    self.btn_study_switch.setChecked(self.engine.enable_study_guard)
                    self._update_study_switch_style(self.engine.enable_study_guard)
                    self.btn_study_switch.blockSignals(False)

        # 6. Synchronize System Tray State
        if self.tray_icon:
            self.tray_icon.update_tray_state(
                is_active=self.engine.state_machine.is_active,
                is_emergency=self.engine.state_machine.is_emergency_stopped,
                current_mode=self.engine.mode_manager.current_mode_name,
                current_profile=self.engine.config.profile_name,
            )

    def _on_mode_combo_changed(self, idx: int) -> None:
        if idx >= 0 and idx < len(self._mode_list):
            mode = self._mode_list[idx][0]
            self.set_interaction_mode(mode)

    def set_interaction_mode(self, mode: InteractionMode) -> None:
        self.engine.mode_manager.switch_to_mode(mode)
        # Update combo if different
        for i, (m_val, _) in enumerate(self._mode_list):
            if m_val == mode:
                if self.combo_mode.currentIndex() != i:
                    self.combo_mode.blockSignals(True)
                    self.combo_mode.setCurrentIndex(i)
                    self.combo_mode.blockSignals(False)
                break
        self._update_gesture_guide()

    def switch_profile(self, profile_name: str) -> None:
        new_cfg = self.profile_manager.load_profile(profile_name)
        self.engine.config = new_cfg
        self.set_interaction_mode(new_cfg.default_mode)
        if hasattr(self.engine, "cursor_engine"):
            self.engine.cursor_engine.config = new_cfg.cursor

    def show_and_raise(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def restart_camera(self) -> None:
        self.engine.stop()
        self.engine.start()

    def open_onboarding_wizard(self) -> None:
        from app.ui.onboarding_wizard import OnboardingWizardDialog
        dlg = OnboardingWizardDialog(self.engine, self)
        dlg.exec()

    def open_calibration_wizard(self) -> None:
        from app.ui.calibration_dialog import CalibrationDialog
        dlg = CalibrationDialog(self.engine.config, self)
        dlg.exec()

    def open_gesture_editor(self) -> None:
        from app.ui.gesture_editor import GestureEditorWidget
        dlg = QDialog(self)
        dlg.setWindowTitle("GestureOS — Gesture Mappings & Sensitivity")
        dlg.resize(760, 480)
        dlg.setStyleSheet(CLEAN_DARK_THEME)
        layout = QVBoxLayout(dlg)
        layout.addWidget(GestureEditorWidget(self.engine.config, dlg))
        dlg.exec()

    def open_drawing_canvas(self) -> None:
        from app.ui.drawing_widget import DrawingWidget
        drawing_mode = self.engine.mode_manager.get_mode(InteractionMode.DRAWING)
        if drawing_mode is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("GestureOS — Air Drawing Virtual Canvas")
        dlg.resize(800, 600)
        dlg.setStyleSheet(CLEAN_DARK_THEME)
        layout = QVBoxLayout(dlg)
        widget = DrawingWidget(drawing_mode, dlg)
        layout.addWidget(widget)
        # Also switch to drawing mode while canvas is active
        self.set_interaction_mode(InteractionMode.DRAWING)
        dlg.exec()

    def open_diagnostics(self) -> None:
        from app.ui.diagnostics_panel import DiagnosticsPanel
        dlg = QDialog(self)
        dlg.setWindowTitle("GestureOS — System Telemetry & Diagnostics")
        dlg.resize(650, 480)
        dlg.setStyleSheet(CLEAN_DARK_THEME)
        layout = QVBoxLayout(dlg)
        panel = DiagnosticsPanel(self.engine.telemetry, dlg)
        layout.addWidget(panel)

        diag_timer = QTimer(dlg)
        def _tick():
            out = self.engine.latest_output
            if out and out.telemetry:
                panel.update_metrics(out.telemetry)
        diag_timer.timeout.connect(_tick)
        diag_timer.start(100)
        dlg.exec()

    def closeEvent(self, event) -> None:
        self.quit_application()
        event.accept()

    def quit_application(self) -> None:
        self.engine.stop()
        QApplication.quit()
