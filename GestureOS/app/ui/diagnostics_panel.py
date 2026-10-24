"""Developer diagnostics panel displaying live FPS, latency breakdown, and resource utilization."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QGroupBox,
)
from PySide6.QtCore import Qt
from app.diagnostics.telemetry import PerformanceSnapshot, TelemetryCollector


class DiagnosticsPanel(QWidget):
    """Real-time performance metrics and developer telemetry dashboard widget."""

    def __init__(self, telemetry: TelemetryCollector, parent=None) -> None:
        super().__init__(parent)
        self.telemetry = telemetry
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Performance Group
        perf_group = QGroupBox("Engine Latency & Frame Rate")
        perf_group.setStyleSheet("QGroupBox { font-weight: 600; color: #0d6efd; }")
        perf_grid = QGridLayout(perf_group)

        self.lbl_fps = self._create_metric_label("0.0 FPS")
        self.lbl_total_lat = self._create_metric_label("0.0 ms")
        self.lbl_cam_lat = self._create_metric_label("0.0 ms")
        self.lbl_vis_lat = self._create_metric_label("0.0 ms")
        self.lbl_ges_lat = self._create_metric_label("0.0 ms")

        perf_grid.addWidget(QLabel("Pipeline FPS:"), 0, 0)
        perf_grid.addWidget(self.lbl_fps, 0, 1)
        perf_grid.addWidget(QLabel("Total Latency:"), 1, 0)
        perf_grid.addWidget(self.lbl_total_lat, 1, 1)
        perf_grid.addWidget(QLabel("Camera Capture:"), 2, 0)
        perf_grid.addWidget(self.lbl_cam_lat, 2, 1)
        perf_grid.addWidget(QLabel("Vision Detection:"), 3, 0)
        perf_grid.addWidget(self.lbl_vis_lat, 3, 1)
        perf_grid.addWidget(QLabel("Gesture Engine:"), 4, 0)
        perf_grid.addWidget(self.lbl_ges_lat, 4, 1)

        layout.addWidget(perf_group)

        # Resource Utilization Group
        res_group = QGroupBox("System Hardware Footprint")
        res_group.setStyleSheet("QGroupBox { font-weight: 600; color: #198754; }")
        res_grid = QGridLayout(res_group)

        self.lbl_cpu = self._create_metric_label("0.0 %")
        self.lbl_ram = self._create_metric_label("0.0 MB")
        self.lbl_uptime = self._create_metric_label("0.0 s")

        res_grid.addWidget(QLabel("Process CPU Usage:"), 0, 0)
        res_grid.addWidget(self.lbl_cpu, 0, 1)
        res_grid.addWidget(QLabel("Process RAM (RSS):"), 1, 0)
        res_grid.addWidget(self.lbl_ram, 1, 1)
        res_grid.addWidget(QLabel("Session Uptime:"), 2, 0)
        res_grid.addWidget(self.lbl_uptime, 2, 1)

        layout.addWidget(res_group)

        # Action & Accuracy Counters
        count_group = QGroupBox("Gesture & Safety Counters")
        count_group.setStyleSheet("QGroupBox { font-weight: 600; color: #ffc107; }")
        count_grid = QGridLayout(count_group)

        self.lbl_total_g = self._create_metric_label("0")
        self.lbl_filtered_fp = self._create_metric_label("0")
        self.lbl_actions_dispatched = self._create_metric_label("0")

        count_grid.addWidget(QLabel("Total Gestures Detected:"), 0, 0)
        count_grid.addWidget(self.lbl_total_g, 0, 1)
        count_grid.addWidget(QLabel("False Positives Filtered:"), 1, 0)
        count_grid.addWidget(self.lbl_filtered_fp, 1, 1)
        count_grid.addWidget(QLabel("Actions Dispatched:"), 2, 0)
        count_grid.addWidget(self.lbl_actions_dispatched, 2, 1)

        layout.addWidget(count_group)

        # Reset button
        btn_reset = QPushButton("Reset Statistics")
        btn_reset.setStyleSheet(
            "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; padding: 7px 16px; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background-color: #3d434a; }"
        )
        btn_reset.clicked.connect(self.telemetry.reset_statistics)
        layout.addWidget(btn_reset)
        layout.addStretch()

    def _create_metric_label(self, default_text: str) -> QLabel:
        lbl = QLabel(default_text)
        lbl.setStyleSheet("font-weight: 600; color: #f8f9fa;")
        lbl.setAlignment(Qt.AlignRight)
        return lbl

    def update_metrics(self, snapshot: PerformanceSnapshot) -> None:
        self.lbl_fps.setText(f"{snapshot.fps:.1f} FPS")
        self.lbl_total_lat.setText(f"{snapshot.total_latency_ms:.1f} ms")
        self.lbl_cam_lat.setText(f"{snapshot.camera_latency_ms:.1f} ms")
        self.lbl_vis_lat.setText(f"{snapshot.vision_latency_ms:.1f} ms")
        self.lbl_ges_lat.setText(f"{snapshot.gesture_latency_ms:.1f} ms")

        self.lbl_cpu.setText(f"{snapshot.cpu_percent:.1f} %")
        self.lbl_ram.setText(f"{snapshot.ram_mb:.1f} MB")
        self.lbl_uptime.setText(f"{int(snapshot.uptime_sec)} s")

        self.lbl_total_g.setText(str(snapshot.total_gestures))
        self.lbl_filtered_fp.setText(str(snapshot.false_positives_filtered))
        self.lbl_actions_dispatched.setText(str(snapshot.actions_dispatched))
