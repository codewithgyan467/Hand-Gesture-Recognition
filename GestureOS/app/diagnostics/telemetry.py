"""Real-time performance telemetry, latency profiling, and diagnostics collection for GestureOS."""

from __future__ import annotations
import time
import psutil
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from app.core.events import EventBus, EventType, default_event_bus


@dataclass
class PerformanceSnapshot:
    fps: float = 0.0
    camera_latency_ms: float = 0.0
    vision_latency_ms: float = 0.0
    gesture_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    confidence: float = 0.0
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    uptime_sec: float = 0.0
    total_gestures: int = 0
    false_positives_filtered: int = 0
    actions_dispatched: int = 0
    current_gesture: str = "none"
    current_mode: str = "Mouse"
    state: str = "inactive"


class TelemetryCollector:
    """Collects rolling metrics, computes FPS and latencies, and reports diagnostics."""

    def __init__(self, window_size: int = 30, event_bus: Optional[EventBus] = None) -> None:
        self._window_size = window_size
        self._event_bus = event_bus or default_event_bus
        self._start_time = time.time()
        self._process = psutil.Process()

        # Rolling buffers
        self._frame_times = deque(maxlen=window_size)
        self._camera_latencies = deque(maxlen=window_size)
        self._vision_latencies = deque(maxlen=window_size)
        self._gesture_latencies = deque(maxlen=window_size)
        self._confidences = deque(maxlen=window_size)

        # Counters
        self._total_gestures: int = 0
        self._false_positives_filtered: int = 0
        self._actions_dispatched: int = 0

        # Current state labels
        self.current_gesture: str = "none"
        self.current_mode: str = "Mouse"
        self.current_state: str = "inactive"

        self._last_system_metric_time: float = 0.0
        self._cached_cpu: float = 0.0
        self._cached_ram: float = 0.0

    def record_frame(
        self,
        camera_ms: float,
        vision_ms: float,
        gesture_ms: float,
        confidence: float = 0.0,
    ) -> None:
        now = time.time()
        self._frame_times.append(now)
        self._camera_latencies.append(camera_ms)
        self._vision_latencies.append(vision_ms)
        self._gesture_latencies.append(gesture_ms)
        self._confidences.append(confidence)

    def record_gesture(self, gesture_name: str) -> None:
        self._total_gestures += 1
        self.current_gesture = gesture_name

    def record_false_positive_filtered(self) -> None:
        self._false_positives_filtered += 1

    def record_action_dispatched(self) -> None:
        self._actions_dispatched += 1

    def get_snapshot(self) -> PerformanceSnapshot:
        now = time.time()

        # Compute FPS
        fps = 0.0
        if len(self._frame_times) >= 2:
            duration = self._frame_times[-1] - self._frame_times[0]
            if duration > 0:
                fps = (len(self._frame_times) - 1) / duration

        # Compute average latencies
        avg_cam = sum(self._camera_latencies) / len(self._camera_latencies) if self._camera_latencies else 0.0
        avg_vis = sum(self._vision_latencies) / len(self._vision_latencies) if self._vision_latencies else 0.0
        avg_ges = sum(self._gesture_latencies) / len(self._gesture_latencies) if self._gesture_latencies else 0.0
        total_lat = avg_cam + avg_vis + avg_ges
        avg_conf = sum(self._confidences) / len(self._confidences) if self._confidences else 0.0

        # Rate-limit psutil queries (every 0.5s)
        if now - self._last_system_metric_time >= 0.5:
            try:
                self._cached_cpu = self._process.cpu_percent()
                self._cached_ram = self._process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
            self._last_system_metric_time = now

        snapshot = PerformanceSnapshot(
            fps=round(fps, 1),
            camera_latency_ms=round(avg_cam, 2),
            vision_latency_ms=round(avg_vis, 2),
            gesture_latency_ms=round(avg_ges, 2),
            total_latency_ms=round(total_lat, 2),
            confidence=round(avg_conf, 2),
            cpu_percent=round(self._cached_cpu, 1),
            ram_mb=round(self._cached_ram, 1),
            uptime_sec=round(now - self._start_time, 1),
            total_gestures=self._total_gestures,
            false_positives_filtered=self._false_positives_filtered,
            actions_dispatched=self._actions_dispatched,
            current_gesture=self.current_gesture,
            current_mode=self.current_mode,
            state=self.current_state,
        )

        return snapshot

    def reset_statistics(self) -> None:
        self._total_gestures = 0
        self._false_positives_filtered = 0
        self._actions_dispatched = 0
        self._start_time = time.time()
