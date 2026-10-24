"""OpenCV-based physical webcam implementation with hotplug/disconnect auto-recovery and zero-latency bounded buffer."""

from __future__ import annotations
import cv2
import sys
import time
import threading
import numpy as np
from typing import Tuple, Optional, List, Dict
from app.camera.base import BaseCamera
from app.core.events import EventBus, EventType, default_event_bus
from app.diagnostics.logger import get_logger

logger = get_logger("camera")


def discover_cameras(max_to_test: int = 6) -> List[Dict[str, Any]]:
    """Probes video capture indices to discover physically connected cameras and their capabilities."""
    available: List[Dict[str, Any]] = []
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY

    for idx in range(max_to_test):
        try:
            cap = cv2.VideoCapture(idx, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
                    available.append({
                        "index": idx,
                        "name": f"Camera {idx} ({w}x{h} @ {fps}fps)",
                        "width": w,
                        "height": h,
                        "fps": fps,
                    })
                cap.release()
        except Exception:
            pass
    return available


class OpenCVCamera(BaseCamera):
    """Production OpenCV camera driver with dedicated capture thread, bounded 1-frame queue, and auto-reconnection."""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        mirror: bool = True,
        auto_reconnect: bool = True,
        reconnect_interval_sec: float = 2.0,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.camera_index = camera_index
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.mirror = mirror
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval_sec = reconnect_interval_sec
        self._event_bus = event_bus or default_event_bus

        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._is_running = False
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._is_disconnected = False

        # Zero-latency bounded buffer (latest frame only)
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_timestamp: float = 0.0
        self._new_frame_event = threading.Event()

        self._capture_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_bounded(self) -> bool:
        return True

    def start(self) -> bool:
        with self._lock:
            self._stop_event.clear()
            self._is_running = True
            success = self._open_device()
            if not success:
                logger.error(f"Failed to open camera index {self.camera_index}")
                self._is_disconnected = True
                self._event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {
                    "status": "disconnected",
                    "camera_index": self.camera_index,
                })
                if self.auto_reconnect:
                    self._start_reconnect_worker()
                return False

            self._is_disconnected = False
            self._start_capture_worker()

            self._event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {
                "status": "connected",
                "camera_index": self.camera_index,
            })
            return True

    def _open_device(self) -> bool:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass

        # Use DirectShow on Windows for fast enumeration, default on others
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.camera_index, backend)
        if not cap.isOpened() and backend != cv2.CAP_ANY:
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            return False

        # Resolution & FPS negotiation
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self._cap = cap
        self._consecutive_failures = 0
        return True

    def _start_capture_worker(self) -> None:
        if self._capture_thread and self._capture_thread.is_alive():
            return
        self._capture_thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="CameraCaptureWorker"
        )
        self._capture_thread.start()

    def _capture_loop(self) -> None:
        """Dedicated high-priority capture thread continuously draining hardware frames."""
        while not self._stop_event.is_set() and self._is_running:
            if self._is_disconnected or self._cap is None:
                time.sleep(0.05)
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None or frame.size == 0:
                self._handle_read_failure()
                time.sleep(0.02)
                continue

            self._consecutive_failures = 0
            if self.mirror:
                frame = cv2.flip(frame, 1)

            # Store in bounded 1-frame buffer, instantly overwriting old frame
            with self._lock:
                self._latest_frame = frame
                self._latest_timestamp = time.time()
                self._new_frame_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._is_running = False

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)
            self._capture_thread = None

        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
            self._latest_frame = None

        logger.info("Camera capture stopped.")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Retrieves the newest captured camera frame without queue lag."""
        if not self._is_running or self._is_disconnected:
            return (False, None)

        with self._lock:
            if self._latest_frame is not None:
                return (True, self._latest_frame.copy())
            return (False, None)

    def _handle_read_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures and not self._is_disconnected:
            self._is_disconnected = True
            logger.warning("Camera hardware disconnected or lost signal!")
            self._event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {
                "status": "disconnected",
                "camera_index": self.camera_index,
            })
            if self.auto_reconnect:
                self._start_reconnect_worker()

    def _start_reconnect_worker(self) -> None:
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True, name="CameraReconnectWorker"
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        logger.info("Starting camera reconnection daemon...")
        while not self._stop_event.is_set() and self._is_disconnected and self._is_running:
            time.sleep(self.reconnect_interval_sec)
            with self._lock:
                success = self._open_device()
                if success:
                    self._is_disconnected = False
                    logger.info("Camera successfully reconnected!")
                    self._event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {
                        "status": "reconnected",
                        "camera_index": self.camera_index,
                    })
                    self._start_capture_worker()
                    break

    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened() and not self._is_disconnected

    def get_resolution(self) -> Tuple[int, int]:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                return (w, h)
        return (self.target_width, self.target_height)

    def set_resolution(self, width: int, height: int) -> bool:
        with self._lock:
            self.target_width = width
            self.target_height = height
            if self._cap is not None and self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                return True
        return False

    def set_fps(self, fps: int) -> bool:
        with self._lock:
            self.target_fps = fps
            if self._cap is not None and self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FPS, fps)
                return True
        return False

    def get_camera_name(self) -> str:
        return f"Camera {self.camera_index} (OpenCV Backend)"
