"""Interactive first-launch onboarding wizard for GestureOS."""

from __future__ import annotations
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
)
from PySide6.QtCore import Qt, QTimer
from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.calibration.profile_manager import ProfileManager


class OnboardingWizardDialog(QDialog):
    """Interactive 6-step guided wizard for setting up GestureOS touchless control."""

    def __init__(self, engine: GestureOSEngine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.profile_manager = ProfileManager()

        self.setWindowTitle("GestureOS — Quick Setup & Calibration Wizard")
        self.resize(720, 520)
        self.setStyleSheet("""
            QDialog { background-color: #212529; color: #dee2e6; }
            QLabel, QPushButton, QComboBox { font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", Arial, sans-serif; }
            QLabel { color: #dee2e6; }
            QPushButton {
                background-color: #343a40; color: #ffffff; border: 1px solid #495057;
                padding: 8px 18px; border-radius: 6px; font-weight: 500; font-size: 13px;
            }
            QPushButton:hover { background-color: #3d434a; border-color: #6c757d; }
            QPushButton#PrimaryBtn {
                background-color: #0d6efd; border: 1px solid #0d6efd; font-weight: 500; color: #ffffff;
            }
            QPushButton#PrimaryBtn:hover { background-color: #0b5ed7; border-color: #0a58ca; }
            QComboBox {
                background-color: #2b3035; border: 1px solid #495057; padding: 6px 12px;
                border-radius: 6px; color: #dee2e6; font-size: 13px; font-weight: 400;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # Header Progress
        header_row = QHBoxLayout()
        self.lbl_step = QLabel("Step 1 of 6: Camera Setup")
        self.lbl_step.setStyleSheet("font-size: 13px; font-weight: 600; color: #0d6efd;")
        header_row.addWidget(self.lbl_step)
        header_row.addStretch()
        main_layout.addLayout(header_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(1, 6)
        self.progress_bar.setValue(1)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #343a40; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #0d6efd; border-radius: 3px; }
        """)
        main_layout.addWidget(self.progress_bar)

        # Stacked Pages
        self.stack = QStackedWidget()

        # Step 1: Camera
        p1 = self._build_page(
            "📷 Camera Device Selection",
            "GestureOS uses your webcam to track hands in real time. Processing is 100% local and private.",
            "Make sure your webcam is pointed towards your sitting position with adequate room lighting.",
        )
        self.stack.addWidget(p1)

        # Step 2: Hand Detection
        p2 = self._build_page(
            "🖐 Hand Detection & Calibration",
            "Hold your hand up in front of the camera inside the frame.",
            "The MediaPipe AI neural landmarker automatically detects 21 joints on your fingers and palm.",
        )
        self.stack.addWidget(p2)

        # Step 3: Pointer Reach
        p3 = self._build_page(
            "🎯 Screen-Corner Reachability",
            "GestureOS uses an Active Region box so you can reach all 4 screen corners comfortably.",
            "Moving your hand slightly within the central camera area maps across your entire desktop.",
        )
        self.stack.addWidget(p3)

        # Step 4: Pinch to Click
        p4 = self._build_page(
            "🤏 Pinch to Click & Drag",
            "Pinch your Thumb and Index finger together to click.",
            "• Quick Tap (< 0.35s): Left Click\n• Hold Pinch (> 0.35s): Drag & Drop / Select Text\n• Thumb + Middle Finger: Right Click",
        )
        self.stack.addWidget(p4)

        # Step 5: Choose Profile
        p5 = QWidget()
        p5_vbox = QVBoxLayout(p5)
        p5_vbox.setSpacing(12)
        lbl_p5_title = QLabel("⚙ Select Starting Profile")
        lbl_p5_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f8f9fa;")
        lbl_p5_desc = QLabel("Choose a pre-tuned profile optimized for your primary workflow:")
        lbl_p5_desc.setStyleSheet("color: #adb5bd; font-size: 13px;")
        p5_vbox.addWidget(lbl_p5_title)
        p5_vbox.addWidget(lbl_p5_desc)

        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["Default (Balanced)", "Presentation", "Media", "Accessibility (Extra Smooth)", "Gaming (Fast)"])
        p5_vbox.addWidget(self.combo_profile)
        p5_vbox.addStretch()
        self.stack.addWidget(p5)

        # Step 6: Ready
        p6 = self._build_page(
            "🎉 You're All Set!",
            "GestureOS touchless computer control is calibrated and ready to use.",
            "• Hold Closed Fist to temporarily pause cursor\n• Press Ctrl+Space anytime to toggle control\n• Press ESC for instant Emergency Safety Stop",
        )
        self.stack.addWidget(p6)

        main_layout.addWidget(self.stack, 1)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self._prev_step)
        self.btn_back.setEnabled(False)
        btn_row.addWidget(self.btn_back)

        btn_row.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryBtn")
        self.btn_next.clicked.connect(self._next_step)
        btn_row.addWidget(self.btn_next)

        main_layout.addLayout(btn_row)

    def _build_page(self, title: str, subtitle: str, details: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 16px; font-weight: 600; color: #f8f9fa;")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 14px; color: #0d6efd; font-weight: 500;")
        lbl_det = QLabel(details)
        lbl_det.setWordWrap(True)
        lbl_det.setStyleSheet("font-size: 13px; color: #adb5bd; line-height: 1.5;")

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_sub)
        layout.addWidget(lbl_det)
        layout.addStretch()
        return page

    def _next_step(self) -> None:
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_navigation(idx + 1)
        else:
            # Finish
            chosen_prof = self.combo_profile.currentText().split(" ")[0]
            if chosen_prof in self.profile_manager.list_profiles():
                self.engine.config = self.profile_manager.load_profile(chosen_prof)
            self.accept()

    def _prev_step(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_navigation(idx - 1)

    def _update_navigation(self, step_idx: int) -> None:
        step_num = step_idx + 1
        total = self.stack.count()
        self.progress_bar.setValue(step_num)

        titles = [
            "Camera Setup",
            "Hand Detection",
            "Screen Reachability",
            "Pinch to Click",
            "Choose Profile",
            "Finished",
        ]
        self.lbl_step.setText(f"Step {step_num} of {total}: {titles[step_idx]}")
        self.btn_back.setEnabled(step_idx > 0)
        self.btn_next.setText("Finish & Start Touchless Control" if step_idx == total - 1 else "Next")
