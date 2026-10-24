"""Comprehensive 14-Step First-Run Setup Wizard for GestureOS + StudyGuard."""

from __future__ import annotations
import sys
import time
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QProgressBar,
    QFrame,
    QSlider,
    QCheckBox,
    QScrollArea,
    QTextEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap

from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.core.resources import ResourceManager
from app.platform.capabilities import PlatformCapabilities
from app.platform.factory import get_platform_controller
from app.platform.audio import get_audio_provider
from app.diagnostics.hardware import HardwareProfiler
from app.calibration.profile_manager import ProfileManager
from app.diagnostics.logger import get_logger

logger = get_logger("setup_wizard")


class SetupWizardDialog(QDialog):
    """14-Step Comprehensive First-Run Setup & Diagnostic Wizard."""

    def __init__(self, engine: GestureOSEngine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config = engine.config
        self.profile_manager = ProfileManager()
        self.hardware_info = HardwareProfiler.detect()
        self.capabilities = PlatformCapabilities.detect()

        self.setWindowTitle("GestureOS — System Setup & Hardware Calibration")
        self.resize(780, 580)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: #e0e0e0; }
            QLabel, QPushButton, QComboBox, QSlider {
                font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            }
            QLabel { color: #e0e0e0; }
            QPushButton {
                background-color: #2b2b36; color: #ffffff; border: 1px solid #3d3d4e;
                padding: 8px 18px; border-radius: 6px; font-weight: 500; font-size: 13px;
            }
            QPushButton:hover { background-color: #383847; border-color: #525268; }
            QPushButton#PrimaryBtn {
                background-color: #0d6efd; border: 1px solid #0d6efd; color: #ffffff;
            }
            QPushButton#PrimaryBtn:hover { background-color: #0b5ed7; }
            QComboBox {
                background-color: #2b2b36; border: 1px solid #3d3d4e; padding: 6px 12px;
                border-radius: 6px; color: #e0e0e0; font-size: 13px;
            }
            QProgressBar {
                background-color: #2b2b36; border-radius: 3px; border: none;
            }
            QProgressBar::chunk {
                background-color: #0d6efd; border-radius: 3px;
            }
        """)

        self._preview_timer: Optional[QTimer] = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 20)
        main_layout.setSpacing(16)

        # Header Info
        header = QHBoxLayout()
        self.lbl_step = QLabel("Step 1 of 14: Welcome to GestureOS")
        self.lbl_step.setStyleSheet("font-size: 14px; font-weight: 600; color: #3b82f6;")
        header.addWidget(self.lbl_step)
        header.addStretch()
        main_layout.addLayout(header)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(1, 14)
        self.progress_bar.setValue(1)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Stacked Pages
        self.stack = QStackedWidget()

        # Step 1: Welcome
        self.stack.addWidget(self._build_step_welcome())
        # Step 2: Platform Detection
        self.stack.addWidget(self._build_step_platform())
        # Step 3: Hardware Capability Detection
        self.stack.addWidget(self._build_step_hardware())
        # Step 4: Camera Detection
        self.stack.addWidget(self._build_step_camera())
        # Step 5: Model Validation
        self.stack.addWidget(self._build_step_models())
        # Step 6: Audio Validation
        self.stack.addWidget(self._build_step_audio())
        # Step 7: Permissions
        self.stack.addWidget(self._build_step_permissions())
        # Step 8: Camera Preview
        self.stack.addWidget(self._build_step_preview())
        # Step 9: Hand Calibration
        self.stack.addWidget(self._build_step_hand_calib())
        # Step 10: Gesture Calibration
        self.stack.addWidget(self._build_step_gesture_calib())
        # Step 11: Cursor Calibration
        self.stack.addWidget(self._build_step_cursor_calib())
        # Step 12: Test Gestures
        self.stack.addWidget(self._build_step_test_gestures())
        # Step 13: Save Profile
        self.stack.addWidget(self._build_step_save_profile())
        # Step 14: Finish
        self.stack.addWidget(self._build_step_finish())

        main_layout.addWidget(self.stack, 1)

        # Bottom Navigation
        btn_bar = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self._prev_step)
        self.btn_back.setEnabled(False)
        btn_bar.addWidget(self.btn_back)

        btn_bar.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryBtn")
        self.btn_next.clicked.connect(self._next_step)
        btn_bar.addWidget(self.btn_next)

        main_layout.addLayout(btn_bar)

    # --- Step Page Builders ---

    def _build_step_welcome(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)
        t = QLabel("👋 Welcome to GestureOS + StudyGuard")
        t.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        v.addWidget(t)

        sub = QLabel(
            "Universal Local Touchless Desktop Interaction Platform with Optional Focus & Hydration Assistant."
        )
        sub.setStyleSheet("font-size: 14px; color: #3b82f6; font-weight: 500;")
        sub.setWordWrap(True)
        v.addWidget(sub)

        desc = QLabel(
            "• 100% Offline & Private: No camera images or telemetry leave your machine.\n"
            "• Touchless Control: Control cursor, clicks, drags, media, and presentations with natural hand gestures.\n"
            "• Intelligent StudyGuard: Detects book closures, phone distractions, and promotes healthy hydration.\n"
            "• Fail-Safe Design: Immediate emergency stop releases mouse and keyboard buttons whenever requested.\n\n"
            "This setup wizard will guide you through hardware verification, calibration, and profile selection."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #a1a1aa; line-height: 1.6;")
        v.addWidget(desc)
        v.addStretch()
        return w

    def _build_step_platform(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🖥 Platform & OS Abstraction")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        info = QLabel(
            f"• Operating System: {self.capabilities.system.capitalize()} {self.capabilities.release} ({self.capabilities.architecture})\n"
            f"• Platform Driver: {'Native Win32 ctypes' if self.capabilities.system == 'windows' else 'PyAutoGUI / X11 / Quartz'}\n"
            f"• Native Mouse Injection: {'✓ Available' if self.capabilities.has_native_mouse else '✗ Unavailable'}\n"
            f"• Native Audio Provider: {'✓ Windows MCI' if self.capabilities.has_mci_audio else '✓ Cross-Platform CLI'}\n"
            f"• Global Emergency Stop Hook: {'✓ pynput Active' if self.capabilities.has_global_hotkeys else '✗ Keyboard Only'}\n"
            f"• Foreground App Detection: {'✓ Available' if self.capabilities.has_foreground_app_detection else '✗ Fallback Mode'}"
        )
        info.setStyleSheet("font-size: 13px; color: #d4d4d8; font-family: monospace; line-height: 1.8;")
        v.addWidget(info)
        v.addStretch()
        return w

    def _build_step_hardware(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("⚡ Hardware Capabilities & Performance Tier")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        hw = self.hardware_info
        info = QLabel(
            f"• CPU: {hw.cpu_name} ({hw.cpu_count_logical} logical cores)\n"
            f"• Memory: {hw.total_ram_gb:.1f} GB RAM ({hw.available_ram_gb:.1f} GB available)\n"
            f"• GPU Acceleration: {hw.gpu_name} (Vendor: {hw.gpu_vendor})\n"
            f"• Primary Display: {hw.primary_display_res} ({hw.monitors_count} monitor{'s' if hw.monitors_count > 1 else ''})\n"
            f"• Assigned Performance Tier: [{hw.recommended_performance_tier}] (Optimized for rock-steady latency)"
        )
        info.setStyleSheet("font-size: 13px; color: #d4d4d8; font-family: monospace; line-height: 1.8;")
        v.addWidget(info)

        tier_lbl = QLabel("You can adjust this tier at any time under Settings → Performance.")
        tier_lbl.setStyleSheet("color: #71717a; font-size: 12px;")
        v.addWidget(tier_lbl)
        v.addStretch()
        return w

    def _build_step_camera(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("📷 Camera Detection & Resolution")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel("Detected camera devices. Select your preferred camera for tracking:")
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        self.cam_combo = QComboBox()
        self.cam_combo.addItem("Camera Index 0 (Default Webcam)", 0)
        self.cam_combo.addItem("Camera Index 1 (External Webcam)", 1)
        self.cam_combo.addItem("Simulation Camera (Virtual Testing)", -1)
        v.addWidget(self.cam_combo)

        info = QLabel(
            "Target Resolution: 640 x 480 @ 30 FPS\n"
            "Bounded Queue: Zero latency with automatic stale frame discarding."
        )
        info.setStyleSheet("color: #10b981; font-size: 12px; font-family: monospace;")
        v.addWidget(info)
        v.addStretch()
        return w

    def _build_step_models(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🧠 Neural Model Validation")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        model_stat = ResourceManager.validate_models()
        lines = []
        for m_name, ok in model_stat.items():
            status = "✓ Ready" if ok else "✗ Missing"
            lines.append(f"• {m_name.replace('_', ' ').title()}: {status}")

        info = QLabel("\n".join(lines))
        info.setStyleSheet("font-size: 13px; color: #d4d4d8; font-family: monospace; line-height: 1.8;")
        v.addWidget(info)

        note = QLabel(
            "Models are loaded lazily. StudyGuard models consume zero memory when StudyGuard is disabled."
        )
        note.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        v.addWidget(note)
        v.addStretch()
        return w

    def _build_step_audio(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🔊 Audio System Validation")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        audio_stat = ResourceManager.validate_audio_assets()
        lines = []
        for a_name, ok in audio_stat.items():
            status = "✓ Found" if ok else "⚠ Missing (Gracefully skipped)"
            lines.append(f"• {a_name.replace('_', ' ').title()}: {status}")

        info = QLabel("\n".join(lines))
        info.setStyleSheet("font-size: 13px; color: #d4d4d8; font-family: monospace; line-height: 1.8;")
        v.addWidget(info)

        btn_test_audio = QPushButton("Test Audio Playback")
        btn_test_audio.clicked.connect(self._test_audio_play)
        v.addWidget(btn_test_audio)
        v.addStretch()
        return w

    def _test_audio_play(self) -> None:
        try:
            player = get_audio_provider()
            sample_path = ResourceManager.get_study_audio_paths().get("kyu_nahi")
            if sample_path:
                player.play(sample_path, volume=0.5)
        except Exception as e:
            logger.warning(f"Audio test failed: {e}")

    def _build_step_permissions(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🛡 Privacy & Operating System Permissions")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        info = QLabel(
            "• Webcam Access: Required for live vision gesture tracking.\n"
            "• Virtual Input Injection: Required to control OS mouse and keyboard.\n"
            "• Global Keyboard Listener: Required for ESC key Emergency Stop.\n"
            "• Zero Telemetry Guarantee: Camera frames are never saved or transmitted."
        )
        info.setStyleSheet("font-size: 13px; color: #d4d4d8; line-height: 1.8;")
        v.addWidget(info)
        v.addStretch()
        return w

    def _build_step_preview(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("👁 Camera Feed Preview")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        self.preview_label = QLabel("Camera feed preview active.\nHold your hand in front of the lens.")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #121216; border: 1px solid #2b2b36; border-radius: 8px; min-height: 240px; color: #71717a;")
        v.addWidget(self.preview_label)
        v.addStretch()
        return w

    def _build_step_hand_calib(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🖐 Hand Calibration & Active Region")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel(
            "Configure your preferred hand and screen mapping reachability:"
        )
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        self.hand_combo = QComboBox()
        self.hand_combo.addItems(["Right Hand (Dominant)", "Left Hand (Dominant)", "Dual Hand (Both)"])
        v.addWidget(self.hand_combo)

        info = QLabel(
            "Active region box: 15% inner margin ensures comfortable reach across multi-monitor setups."
        )
        info.setStyleSheet("color: #71717a; font-size: 12px;")
        v.addWidget(info)
        v.addStretch()
        return w

    def _build_step_gesture_calib(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🤏 Gesture Sensitivity Calibration")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel(
            "Adjust pinch and click detection thresholds for your personal hand size:"
        )
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        lbl_sens = QLabel("Pinch Sensitivity:")
        v.addWidget(lbl_sens)
        self.slider_pinch = QSlider(Qt.Horizontal)
        self.slider_pinch.setRange(20, 80)
        self.slider_pinch.setValue(45)
        v.addWidget(self.slider_pinch)

        v.addStretch()
        return w

    def _build_step_cursor_calib(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🎯 Cursor Speed & One Euro Smoothing")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel(
            "One Euro Filter adapts dynamically: high smoothing when still, zero latency when moving fast."
        )
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        lbl_spd = QLabel("Cursor Tracking Speed:")
        v.addWidget(lbl_spd)
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(10, 30)
        self.slider_speed.setValue(18)
        v.addWidget(self.slider_speed)

        v.addStretch()
        return w

    def _build_step_test_gestures(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("🧪 Gesture Practice & Validation")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel("Try these gestures in front of your camera:")
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        gestures = QLabel(
            "• Index Pointer ☝ → Move cursor\n"
            "• Quick Pinch 👌 → Left click\n"
            "• Hold Pinch 🤏 → Drag & drop\n"
            "• Closed Fist ✊ → Pause cursor\n"
            "• Thumbs Up 👍 → Scroll Up\n"
            "• Thumbs Down 👎 → Scroll Down\n"
            "• Peace Sign ✌ → Play / Pause Media\n"
            "• Dual Fists ✊✊ → Emergency Stop"
        )
        gestures.setStyleSheet("font-size: 13px; color: #d4d4d8; line-height: 1.8;")
        v.addWidget(gestures)
        v.addStretch()
        return w

    def _build_step_save_profile(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)
        t = QLabel("💾 Save Starting Profile")
        t.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        v.addWidget(t)

        desc = QLabel("Select an initial profile configuration:")
        desc.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        v.addWidget(desc)

        self.prof_combo = QComboBox()
        self.prof_combo.addItems([
            "Default (General Productivity)",
            "Media (VLC / YouTube / Spotify)",
            "Presentation (PowerPoint / Keynote)",
            "Browser (Chrome / Edge / Firefox)",
            "Accessibility (Smooth & High Contrast)",
            "Gaming (Ultra-Fast Response)",
            "Study (Focus & Hydration)",
            "Custom (User Mapped)",
        ])
        v.addWidget(self.prof_combo)
        v.addStretch()
        return w

    def _build_step_finish(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(14)
        t = QLabel("🎉 Setup Complete & Ready!")
        t.setStyleSheet("font-size: 18px; font-weight: 700; color: #10b981;")
        v.addWidget(t)

        desc = QLabel(
            "Your hardware is calibrated and GestureOS is ready for touchless interaction.\n\n"
            "Important Safety Reminders:\n"
            "• Press [ESC] at any time for instant Emergency Stop.\n"
            "• Press [Ctrl + Space] to toggle active tracking on / off.\n"
            "• Open Settings anytime to recalibrate or export diagnostics."
        )
        desc.setStyleSheet("font-size: 13px; color: #d4d4d8; line-height: 1.8;")
        v.addWidget(desc)
        v.addStretch()
        return w

    # --- Navigation Logic ---

    def _next_step(self) -> None:
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav_state(idx + 1)
        else:
            # Apply profile and finish
            sel_text = self.prof_combo.currentText().split(" ")[0]
            if sel_text in self.profile_manager.list_profiles():
                self.engine.config = self.profile_manager.load_profile(sel_text)
            self.accept()

    def _prev_step(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_nav_state(idx - 1)

    def _update_nav_state(self, idx: int) -> None:
        step_num = idx + 1
        total = self.stack.count()
        self.progress_bar.setValue(step_num)
        self.btn_back.setEnabled(idx > 0)

        step_titles = [
            "Welcome to GestureOS",
            "Platform Detection",
            "Hardware Capabilities",
            "Camera Detection",
            "Model Validation",
            "Audio Validation",
            "Privacy & Permissions",
            "Camera Preview",
            "Hand Calibration",
            "Gesture Calibration",
            "Cursor Calibration",
            "Test Gestures",
            "Save Profile",
            "Setup Complete",
        ]
        self.lbl_step.setText(f"Step {step_num} of {total}: {step_titles[idx]}")
        self.btn_next.setText("Finish & Launch GestureOS" if idx == total - 1 else "Next")
