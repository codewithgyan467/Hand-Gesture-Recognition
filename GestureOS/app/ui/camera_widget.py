"""High-performance Qt video display widget rendering OpenCV BGR frames as QImage/QPixmap."""

from __future__ import annotations
import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy


class CameraWidget(QLabel):
    """Renders video frames with aspect-ratio preservation and low latency."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 240)
        self.setStyleSheet("background-color: #1a1d20; border-radius: 6px; border: 1px solid #373b3e; color: #adb5bd;")
        self.setText("Camera initializing...")

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        """Converts BGR frame to QPixmap and paints to widget."""
        if frame_bgr is None or frame_bgr.size == 0:
            return

        h, w, ch = frame_bgr.shape
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        bytes_per_line = ch * w

        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(q_img)

        # Scale smoothly while keeping aspect ratio
        scaled = pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
