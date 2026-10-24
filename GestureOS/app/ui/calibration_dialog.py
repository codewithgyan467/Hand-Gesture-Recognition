"""Calibration Wizard Dialog guiding users through 8-step setup."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QWidget,
)
from PySide6.QtCore import Qt
from app.calibration.calibration_wizard import CalibrationWizardEngine, CalibrationStep
from app.core.config import GestureOSConfig


class CalibrationDialog(QDialog):
    """Interactive modal dialog hosting the 8-step calibration wizard."""

    def __init__(self, config: GestureOSConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("GestureOS Calibration Wizard")
        self.resize(540, 360)
        self.setStyleSheet(
            "QDialog { background-color: #212529; color: #dee2e6; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', Arial, sans-serif; }"
        )

        self.engine = CalibrationWizardEngine(config)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Step indicator
        self.lbl_title = QLabel("Step 1 of 8: Camera Positioning")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #0d6efd;")
        layout.addWidget(self.lbl_title)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(12)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #343a40; border-radius: 4px; height: 8px; text-align: center; border: 1px solid #495057; }"
            "QProgressBar::chunk { background-color: #0d6efd; border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        # Instructions
        self.lbl_instructions = QLabel(self.engine.instruction_text)
        self.lbl_instructions.setWordWrap(True)
        self.lbl_instructions.setStyleSheet("font-size: 13px; line-height: 1.5; color: #dee2e6; min-height: 80px;")
        layout.addWidget(self.lbl_instructions)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setStyleSheet(
            "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; padding: 7px 16px; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background-color: #3d434a; }"
        )
        self.btn_prev.clicked.connect(self._on_prev)
        btn_layout.addWidget(self.btn_prev)

        btn_layout.addStretch()

        self.btn_next = QPushButton("Next Step")
        self.btn_next.setStyleSheet(
            "QPushButton { background-color: #0d6efd; color: #ffffff; border: 1px solid #0d6efd; padding: 7px 18px; font-weight: 500; border-radius: 6px; }"
            "QPushButton:hover { background-color: #0b5ed7; }"
        )
        self.btn_next.clicked.connect(self._on_next)
        btn_layout.addWidget(self.btn_next)

        self.btn_finish = QPushButton("Complete Calibration")
        self.btn_finish.setStyleSheet(
            "QPushButton { background-color: #198754; color: #ffffff; border: 1px solid #198754; padding: 7px 18px; font-weight: 500; border-radius: 6px; }"
            "QPushButton:hover { background-color: #157347; }"
        )
        self.btn_finish.clicked.connect(self.accept)
        self.btn_finish.hide()
        btn_layout.addWidget(self.btn_finish)

        layout.addLayout(btn_layout)

    def _on_next(self) -> None:
        step = self.engine.advance_step()
        self._update_display(step)

    def _on_prev(self) -> None:
        step = self.engine.previous_step()
        self._update_display(step)

    def _update_display(self, step: CalibrationStep) -> None:
        idx = step.value
        total = 8
        pct = int((min(idx, total) / total) * 100)
        self.progress_bar.setValue(pct)

        if step == CalibrationStep.COMPLETED:
            self.lbl_title.setText("Calibration Complete!")
            self.lbl_instructions.setText("Your personalized hand scale, active control region, and pinch thresholds are now tuned and saved.")
            self.btn_next.hide()
            self.btn_prev.hide()
            self.btn_finish.show()
        else:
            self.lbl_title.setText(f"Step {idx} of {total}: {step.name.replace('_', ' ').title()}")
            self.lbl_instructions.setText(self.engine.instruction_text)
            self.btn_prev.setEnabled(idx > 1)
