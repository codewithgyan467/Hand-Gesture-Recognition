"""Comprehensive Settings & Preferences Dialog for GestureOS + StudyGuard."""

from __future__ import annotations
import sys
import os
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QSlider,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QScrollArea,
    QFileDialog,
)
from PySide6.QtCore import Qt

from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.core.resources import ResourceManager
from app.platform.capabilities import PlatformCapabilities
from app.diagnostics.hardware import HardwareProfiler
from app.diagnostics.logger import get_logger

logger = get_logger("settings_dialog")


class SettingsDialog(QDialog):
    """Unified Settings Dialog supporting General, Camera, Gestures, StudyGuard, Accessibility, Privacy, and Performance."""

    def __init__(self, engine: GestureOSEngine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config = engine.config

        self.setWindowTitle("GestureOS — Settings & Preferences")
        self.resize(740, 560)
        self.setStyleSheet("""
            QDialog { background-color: #212529; color: #dee2e6; }
            QTabWidget::pane { border: 1px solid #373b3e; background-color: #2b3035; border-radius: 6px; }
            QTabBar::tab {
                background-color: #212529; color: #adb5bd; border: 1px solid #373b3e;
                padding: 8px 16px; margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #2b3035; color: #ffffff; border-bottom: 2px solid #0d6efd; font-weight: 600;
            }
            QGroupBox {
                border: 1px solid #373b3e; border-radius: 6px; margin-top: 14px;
                padding-top: 14px; background-color: #2b3035; font-weight: 600; color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left; padding: 2px 8px;
                color: #0d6efd; background-color: #2b3035; border-radius: 4px;
            }
            QPushButton {
                background-color: #343a40; color: #ffffff; border: 1px solid #495057;
                padding: 7px 16px; border-radius: 6px; font-weight: 500; font-size: 13px;
            }
            QPushButton:hover { background-color: #3d434a; border-color: #6c757d; }
            QPushButton#PrimaryBtn { background-color: #0d6efd; border-color: #0d6efd; }
            QPushButton#PrimaryBtn:hover { background-color: #0b5ed7; }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #212529; border: 1px solid #495057; padding: 4px 8px;
                border-radius: 6px; color: #dee2e6; font-size: 13px;
            }
            QCheckBox { color: #dee2e6; font-size: 13px; spacing: 8px; }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab_general(), "⚙ General")
        self.tabs.addTab(self._build_tab_camera(), "📷 Camera")
        self.tabs.addTab(self._build_tab_study_guard(), "🎯 StudyGuard")
        self.tabs.addTab(self._build_tab_accessibility(), "♿ Accessibility")
        self.tabs.addTab(self._build_tab_privacy(), "🔒 Privacy")
        self.tabs.addTab(self._build_tab_performance(), "⚡ Performance")

        main_layout.addWidget(self.tabs, 1)

        # Bottom Bar
        btn_bar = QHBoxLayout()
        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_bar.addWidget(btn_reset)

        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self._save_settings)
        btn_bar.addWidget(btn_save)

        main_layout.addLayout(btn_bar)

    def _build_tab_general(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_app = QGroupBox("Application Preferences")
        app_v = QVBoxLayout(box_app)

        self.chk_dark = QCheckBox("Dark Mode Theme (Default)")
        self.chk_dark.setChecked(getattr(self.config, "dark_mode", True))
        app_v.addWidget(self.chk_dark)

        self.chk_tray = QCheckBox("Start Minimized to System Tray")
        self.chk_tray.setChecked(getattr(self.config, "start_minimized_to_tray", False))
        app_v.addWidget(self.chk_tray)

        self.chk_auto_switch = QCheckBox("Auto-Switch Profiles by Foreground Application (PowerPoint, VLC, Browser)")
        self.chk_auto_switch.setChecked(getattr(self.config, "auto_switch_foreground_profiles", False))
        app_v.addWidget(self.chk_auto_switch)

        v.addWidget(box_app)
        v.addStretch()
        return w

    def _build_tab_camera(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_cam = QGroupBox("Capture & Frame Stream")
        cam_v = QVBoxLayout(box_cam)

        row_idx = QHBoxLayout()
        row_idx.addWidget(QLabel("Camera Device Index:"))
        self.spin_cam_idx = QSpinBox()
        self.spin_cam_idx.setRange(0, 8)
        self.spin_cam_idx.setValue(self.config.camera.camera_index)
        row_idx.addWidget(self.spin_cam_idx)
        cam_v.addLayout(row_idx)

        self.chk_mirror = QCheckBox("Mirror Camera Preview Horizontally")
        self.chk_mirror.setChecked(self.config.camera.mirror)
        cam_v.addWidget(self.chk_mirror)

        self.chk_invert_x = QCheckBox("Invert Horizontal Coordinates (Fix Pointer Inversion)")
        self.chk_invert_x.setChecked(self.config.cursor.invert_x)
        cam_v.addWidget(self.chk_invert_x)

        self.chk_overlay = QCheckBox("Show Debug Skeleton & Active Region Target Box")
        self.chk_overlay.setChecked(self.config.show_debug_overlay)
        cam_v.addWidget(self.chk_overlay)

        v.addWidget(box_cam)
        v.addStretch()
        return w

    def _build_tab_study_guard(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_sg = QGroupBox("Focus & Distraction Detection")
        sg_v = QVBoxLayout(box_sg)

        self.chk_sg_enable = QCheckBox("Enable StudyGuard AI Monitor")
        self.chk_sg_enable.setChecked(self.engine.enable_study_guard)
        sg_v.addWidget(self.chk_sg_enable)

        row_conf = QHBoxLayout()
        row_conf.addWidget(QLabel("Detection Confidence Threshold:"))
        self.spin_sg_conf = QDoubleSpinBox()
        self.spin_sg_conf.setRange(0.2, 0.95)
        self.spin_sg_conf.setSingleStep(0.05)
        self.spin_sg_conf.setValue(getattr(self.config.study_guard, "min_confidence", 0.45))
        row_conf.addWidget(self.spin_sg_conf)
        sg_v.addLayout(row_conf)

        row_cd = QHBoxLayout()
        row_cd.addWidget(QLabel("Alert Cooldown Duration (seconds):"))
        self.spin_sg_cooldown = QSpinBox()
        self.spin_sg_cooldown.setRange(3, 60)
        self.spin_sg_cooldown.setValue(int(getattr(self.config.study_guard, "alert_cooldown_sec", 10)))
        row_cd.addWidget(self.spin_sg_cooldown)
        sg_v.addLayout(row_cd)

        v.addWidget(box_sg)
        v.addStretch()
        return w

    def _build_tab_accessibility(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_acc = QGroupBox("Accessibility & Motor Assist")
        acc_v = QVBoxLayout(box_acc)

        self.chk_large_ui = QCheckBox("Large UI Mode (Enhanced Text & Icon Sizing)")
        self.chk_large_ui.setChecked(getattr(self.config.accessibility, "large_ui_mode", False))
        acc_v.addWidget(self.chk_large_ui)

        self.chk_high_contrast = QCheckBox("High Contrast Interface (Maximum Visual Distinction)")
        self.chk_high_contrast.setChecked(getattr(self.config.accessibility, "high_contrast", False))
        acc_v.addWidget(self.chk_high_contrast)

        self.chk_slow_cursor = QCheckBox("Slow Cursor Mode (Heavy Dampening for Tremor Reduction)")
        self.chk_slow_cursor.setChecked(getattr(self.config.accessibility, "slow_cursor", False))
        acc_v.addWidget(self.chk_slow_cursor)

        self.chk_dwell = QCheckBox("Dwell Click (Auto-Click upon Pausing Cursor on Target)")
        self.chk_dwell.setChecked(getattr(self.config.accessibility, "dwell_click_enabled", False))
        acc_v.addWidget(self.chk_dwell)

        row_dwell = QHBoxLayout()
        row_dwell.addWidget(QLabel("Dwell Click Time (sec):"))
        self.spin_dwell_time = QDoubleSpinBox()
        self.spin_dwell_time.setRange(0.4, 3.0)
        self.spin_dwell_time.setSingleStep(0.1)
        self.spin_dwell_time.setValue(getattr(self.config.accessibility, "dwell_time_sec", 1.2))
        row_dwell.addWidget(self.spin_dwell_time)
        acc_v.addLayout(row_dwell)

        v.addWidget(box_acc)
        v.addStretch()
        return w

    def _build_tab_privacy(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_priv = QGroupBox("Privacy & Local Processing Guarantee")
        priv_v = QVBoxLayout(box_priv)

        lbl = QLabel(
            "<b>GestureOS Local-First Privacy Commitment:</b><br><br>"
            "• <b>Zero Cloud Uploads:</b> All MediaPipe & TFLite vision models run entirely on your CPU/GPU.<br>"
            "• <b>No Video Storage:</b> Camera frames exist only in transient RAM buffers for inference and are immediately freed.<br>"
            "• <b>No Telemetry Tracking:</b> No user behavioral data, identifiers, or camera images leave your device.<br>"
            "• <b>Diagnostic Transparency:</b> Diagnostic export reports contain only technical metrics (CPU, FPS, latency, version) and no imagery."
        )
        lbl.setStyleSheet("color: #d4d4d8; font-size: 13px; line-height: 1.6;")
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        priv_v.addWidget(lbl)

        btn_open_logs = QPushButton("Open Local Diagnostics & Logs Directory")
        btn_open_logs.clicked.connect(self._open_logs_dir)
        priv_v.addWidget(btn_open_logs)

        v.addWidget(box_priv)
        v.addStretch()
        return w

    def _open_logs_dir(self) -> None:
        import webbrowser
        log_dir = str(ResourceManager.get_logs_dir())
        try:
            if sys.platform == "win32":
                os.startfile(log_dir)
            else:
                webbrowser.open(log_dir)
        except Exception as e:
            QMessageBox.warning(self, "Directory Access", f"Logs folder: {log_dir}")

    def _build_tab_performance(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)

        box_perf = QGroupBox("Hardware Adaptation & Multi-Rate Decimation")
        perf_v = QVBoxLayout(box_perf)

        row_tier = QHBoxLayout()
        row_tier.addWidget(QLabel("Performance Tier:"))
        self.combo_tier = QComboBox()
        self.combo_tier.addItems([
            "FULL (High-end desktop / Discrete GPU)",
            "BALANCED (Standard laptop / Integrated graphics)",
            "LIGHT (Battery saver / Ultra-portable)",
            "COMPATIBILITY (Legacy hardware / Fallback)",
        ])
        current_tier = getattr(self.config, "performance_tier", "BALANCED").upper()
        for i in range(self.combo_tier.count()):
            if current_tier in self.combo_tier.itemText(i):
                self.combo_tier.setCurrentIndex(i)
                break
        row_tier.addWidget(self.combo_tier)
        perf_v.addLayout(row_tier)

        hw = HardwareProfiler.detect()
        lbl_hw = QLabel(
            f"Detected System: {hw.cpu_name} | {hw.total_ram_gb:.1f} GB RAM | {hw.gpu_name}\n"
            f"Recommended Tier: {hw.recommended_performance_tier}"
        )
        lbl_hw.setStyleSheet("color: #10b981; font-family: monospace; font-size: 12px;")
        perf_v.addWidget(lbl_hw)

        v.addWidget(box_perf)
        v.addStretch()
        return w

    def _reset_defaults(self) -> None:
        if QMessageBox.question(self, "Reset Settings", "Reset all settings to default configuration?") == QMessageBox.Yes:
            self.config = GestureOSConfig()
            self.engine.config = self.config
            self.accept()

    def _save_settings(self) -> None:
        # Save General
        self.config.dark_mode = self.chk_dark.isChecked()
        self.config.start_minimized_to_tray = self.chk_tray.isChecked()
        self.config.auto_switch_foreground_profiles = self.chk_auto_switch.isChecked()

        # Save Camera
        self.config.camera.camera_index = self.spin_cam_idx.value()
        self.config.camera.mirror = self.chk_mirror.isChecked()
        self.engine.camera.mirror = self.config.camera.mirror
        self.config.cursor.invert_x = self.chk_invert_x.isChecked()
        self.engine.cursor_engine.cursor_config.invert_x = self.config.cursor.invert_x
        self.config.show_debug_overlay = self.chk_overlay.isChecked()

        # Save StudyGuard
        self.engine.set_study_guard_enabled(self.chk_sg_enable.isChecked())
        self.config.study_guard.min_confidence = self.spin_sg_conf.value()
        self.config.study_guard.alert_cooldown_sec = float(self.spin_sg_cooldown.value())

        # Save Accessibility
        self.config.accessibility.large_ui_mode = self.chk_large_ui.isChecked()
        self.config.accessibility.high_contrast = self.chk_high_contrast.isChecked()
        self.config.accessibility.slow_cursor = self.chk_slow_cursor.isChecked()
        self.config.accessibility.dwell_click_enabled = self.chk_dwell.isChecked()
        self.config.accessibility.dwell_time_sec = self.spin_dwell_time.value()

        # Save Performance Tier
        selected_tier = self.combo_tier.currentText().split(" ")[0]
        self.config.performance_tier = selected_tier
        if hasattr(self.engine, "performance_controller"):
            self.engine.performance_controller.set_tier(selected_tier)

        self.accept()
