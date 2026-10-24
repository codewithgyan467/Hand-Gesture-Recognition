"""OpenCV-based physical webcam implementation with hotplug/disconnect auto-recovery."""

from __future__ import annotations
import cv2
import time
import threading
import numpy as np
from typing import Tuple, Optional, List
from app.camera.base import BaseCamera
from app.core.events import EventBus, EventType, default_event_bus
from app.diagnostics.logger import get_logger

logger = get_logger("camera")


def discover_cameras(max_to_test: int = 4) -> List[int]:
    """Probes video capture indices to discover physically connected cameras."""
    available: List[int] = []
    for idx in range(max_to_test):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(idx)
            cap.release()
    return available


class OpenCVCamera(BaseCamera):
    """Production OpenCV camera driver with automatic reconnection and frame-drop tolerance."""

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

        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

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

        # Try DirectShow first on Windows for faster initialization, fallback to default
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            return False

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

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self._is_running = False
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None
        logger.info("Camera capture stopped.")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self._is_running or self._is_disconnected:
            return (False, None)

        with self._lock:
            if self._cap is None or not self._cap.isOpened():
                self._handle_read_failure()
                return (False, None)

            ret, frame = self._cap.read()
            if not ret or frame is None or frame.size == 0:
                self._handle_read_failure()
                return (False, None)

            self._consecutive_failures = 0
            if self.mirror:
                frame = cv2.flip(frame, 1)

            return (True, frame)

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
        return f"OpenCV Camera (Index {self.camera_index})"
