"""Debug visualizer drawing hand skeletons, bounding boxes, active zones, and HUD overlays."""

from __future__ import annotations
import cv2
import numpy as np
from typing import List, Optional, Tuple
from app.core.types import HandLandmarks, GestureType, HandLandmarkIndex, Point3D
from app.core.config import ActiveRegionConfig


# Hand skeleton bone connections (pairs of landmark indices)
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring finger
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm base cross connections
    (5, 9), (9, 13), (13, 17),
]

FINGERTIP_INDICES = {4, 8, 12, 16, 20}


class DebugVisualizer:
    """Renders sleek, low-latency computer-vision HUD overlays on OpenCV frames."""

    def __init__(self) -> None:
        pass

    def render_overlay(
        self,
        frame: np.ndarray,
        hands: List[HandLandmarks],
        current_gesture: str = "none",
        confidence: float = 0.0,
        fps: float = 0.0,
        state: str = "inactive",
        mode: str = "Mouse",
        active_region: Optional[ActiveRegionConfig] = None,
        volume_level: Optional[float] = None,
        draw_landmarks: bool = True,
    ) -> np.ndarray:
        """Renders all debug HUD graphics onto a copy or in-place frame."""
        h, w = frame.shape[:2]
        canvas = frame.copy()

        # 1. Draw Active Region Box
        if active_region:
            rx1 = int(active_region.x_min * w)
            ry1 = int(active_region.y_min * h)
            rx2 = int(active_region.x_max * w)
            ry2 = int(active_region.y_max * h)
            cv2.rectangle(canvas, (rx1, ry1), (rx2, ry2), (0, 200, 255), 1, cv2.LINE_AA)
            cv2.putText(canvas, "ACTIVE REGION", (rx1 + 5, ry1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1, cv2.LINE_AA)

        # 2. Draw Hand Landmarks & Skeleton
        if draw_landmarks:
            for hand in hands:
                self._draw_hand_skeleton(canvas, hand, w, h)

        # 3. Draw Top Status HUD Bar
        self._draw_hud_bar(canvas, state, mode, current_gesture, confidence, fps, w)

        # 4. Draw Volume Overlay Bar (if active)
        if volume_level is not None:
            self._draw_volume_bar(canvas, volume_level, w, h)

        return canvas

    def _draw_hand_skeleton(self, canvas: np.ndarray, hand: HandLandmarks, w: int, h: int) -> None:
        pixel_coords = []
        for lm in hand.landmarks:
            px = int(lm.x * w)
            py = int(lm.y * h)
            pixel_coords.append((px, py))

        # Draw bones
        for start_idx, end_idx in HAND_CONNECTIONS:
            pt1 = pixel_coords[start_idx]
            pt2 = pixel_coords[end_idx]
            cv2.line(canvas, pt1, pt2, (120, 240, 255), 2, cv2.LINE_AA)

        # Draw joints
        for i, pt in enumerate(pixel_coords):
            if i in FINGERTIP_INDICES:
                cv2.circle(canvas, pt, 6, (0, 255, 120), -1, cv2.LINE_AA)
                cv2.circle(canvas, pt, 7, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.circle(canvas, pt, 3, (255, 150, 0), -1, cv2.LINE_AA)

        # Draw Bounding Box & Handedness Tag
        xs = [pt[0] for pt in pixel_coords]
        ys = [pt[1] for pt in pixel_coords]
        min_x, max_x = max(0, min(xs) - 10), min(w - 1, max(xs) + 10)
        min_y, max_y = max(0, min(ys) - 10), min(h - 1, max(ys) + 10)
        cv2.rectangle(canvas, (min_x, min_y), (max_x, max_y), (70, 70, 70), 1, cv2.LINE_AA)

        tag = f"{hand.handedness.value} ({int(hand.score * 100)}%)"
        cv2.putText(canvas, tag, (min_x, max(15, min_y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    def _draw_hud_bar(
        self, canvas: np.ndarray, state: str, mode: str, gesture: str, confidence: float, fps: float, w: int
    ) -> None:
        # Semi-transparent background banner across top
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (w, 36), (15, 15, 18), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        # State badge color
        state_color = (0, 255, 120) if state == "active" else (0, 165, 255)
        if state == "emergency_stop":
            state_color = (0, 0, 255)
        elif state == "inactive":
            state_color = (150, 150, 150)

        # Render Left: State and Mode
        cv2.putText(canvas, f"[{state.upper()}]", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, state_color, 2, cv2.LINE_AA)
        cv2.putText(canvas, f"MODE: {mode.upper()}", (125, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (230, 230, 230), 1, cv2.LINE_AA)

        # Render Middle: Gesture
        if gesture != "none":
            g_text = f"GESTURE: {gesture.upper()} ({int(confidence * 100)}%)"
            cv2.putText(canvas, g_text, (int(w * 0.42), 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 240, 255), 2, cv2.LINE_AA)

        # Render Right: FPS
        fps_text = f"{fps:.1f} FPS"
        cv2.putText(canvas, fps_text, (w - 85, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1, cv2.LINE_AA)

    def _draw_volume_bar(self, canvas: np.ndarray, volume_level: float, w: int, h: int) -> None:
        bar_w = 240
        bar_h = 24
        x1 = (w - bar_w) // 2
        y1 = h - 55
        x2 = x1 + bar_w
        y2 = y1 + bar_h

        # Background
        cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 6), (20, 20, 24), -1)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (70, 70, 70), 1)

        # Filled progress
        fill_w = int((volume_level / 100.0) * bar_w)
        cv2.rectangle(canvas, (x1, y1), (x1 + fill_w, y2), (0, 215, 255), -1)

        # Text label
        label = f"VOLUME: {int(volume_level)}%"
        cv2.putText(canvas, label, (x1 + 6, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
