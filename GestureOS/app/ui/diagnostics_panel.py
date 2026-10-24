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

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_reset = QPushButton("Reset Statistics")
        btn_reset.setStyleSheet(
            "QPushButton { background-color: #343a40; color: #ffffff; border: 1px solid #495057; padding: 7px 16px; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background-color: #3d434a; }"
        )
        btn_reset.clicked.connect(self.telemetry.reset_statistics)
        btn_bar.addWidget(btn_reset)

        btn_export = QPushButton("📥 Export Diagnostic Report")
        btn_export.setStyleSheet(
            "QPushButton { background-color: #0d6efd; color: #ffffff; border: 1px solid #0d6efd; padding: 7px 16px; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background-color: #0b5ed7; }"
        )
        btn_export.clicked.connect(self.export_diagnostic_report)
        btn_bar.addWidget(btn_export)

        layout.addLayout(btn_bar)
        layout.addStretch()

    def export_diagnostic_report(self) -> str:
        """Generates and writes a comprehensive local diagnostic JSON report (privacy-safe, no images)."""
        import sys
        import time
        import json
        from PySide6.QtWidgets import QMessageBox
        from app.core.resources import ResourceManager
        from app.platform.capabilities import PlatformCapabilities
        from app.diagnostics.hardware import HardwareProfiler

        snap = self.telemetry.get_snapshot()
        caps = PlatformCapabilities.detect()
        hw = HardwareProfiler.detect()

        report = {
            "version": "1.0.0",
            "timestamp": time.time(),
            "runtime": {
                "python": sys.version,
                "executable": sys.executable,
                "platform": sys.platform,
            },
            "platform_capabilities": caps.to_dict(),
            "hardware": hw.to_dict(),
            "models_ready": ResourceManager.validate_models(),
            "audio_assets_ready": ResourceManager.validate_audio_assets(),
            "performance_summary": {
                "fps": snap.fps,
                "total_latency_ms": snap.total_latency_ms,
                "camera_latency_ms": snap.camera_latency_ms,
                "vision_latency_ms": snap.vision_latency_ms,
                "gesture_latency_ms": snap.gesture_latency_ms,
                "cpu_percent": snap.cpu_percent,
                "ram_mb": snap.ram_mb,
                "uptime_sec": snap.uptime_sec,
                "total_gestures": snap.total_gestures,
                "false_positives_filtered": snap.false_positives_filtered,
                "actions_dispatched": snap.actions_dispatched,
            },
            "privacy_note": "No camera frames, audio samples, or private user files are included in diagnostics."
        }

        logs_dir = ResourceManager.get_logs_dir()
        report_path = logs_dir / f"diagnostic_report_{int(time.time())}.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            QMessageBox.information(
                self,
                "Diagnostic Report Exported",
                f"Diagnostic report safely saved to:\n\n{report_path}\n\n(No images or private data included)"
            )
            return str(report_path)
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not write diagnostic report: {e}")
            return ""

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
