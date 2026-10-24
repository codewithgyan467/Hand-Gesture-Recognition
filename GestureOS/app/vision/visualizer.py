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
        study_result: Optional[Any] = None,
        study_alert: Optional[str] = None,
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

        # 3. Draw StudyGuard Overlays (Book, Phone, Container, Mouth)
        if study_result is not None:
            self._draw_study_overlay(canvas, study_result, w, h)

        # 4. Draw Glowing Meme Alert Banner if active
        if study_alert:
            self._draw_study_alert(canvas, study_alert, w, h)

        # 5. Draw Top Status HUD Bar
        has_study = study_result is not None
        self._draw_hud_bar(canvas, state, mode, current_gesture, confidence, fps, w, study_active=has_study)

        # 6. Draw Volume Overlay Bar (if active)
        if volume_level is not None:
            self._draw_volume_bar(canvas, volume_level, w, h)

        return canvas

    def _draw_study_overlay(self, canvas: np.ndarray, res: Any, w: int, h: int) -> None:
        # Face and Mouth
        if getattr(res, "face_detected", False) and getattr(res, "face_box", None):
            fx1, fy1, fx2, fy2 = res.face_box
            cv2.rectangle(canvas, (fx1, fy1), (fx2, fy2), (180, 105, 255), 2)
            cv2.putText(canvas, "FACE", (fx1, max(15, fy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 105, 255), 1)
            if getattr(res, "mouth_point", None):
                mx, my = res.mouth_point
                cv2.circle(canvas, (mx, my), 5, (255, 105, 180), -1)

        # Book
        if getattr(res, "book_detected", False) and getattr(res, "book_box", None):
            bx1, by1, bx2, by2 = res.book_box
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (0, 220, 100), 2)
            score_txt = f"BOOK: {int(res.book_score * 100)}%"
            cv2.putText(canvas, score_txt, (bx1, max(18, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 100), 2)

        # Phone
        if getattr(res, "phone_detected", False) and getattr(res, "phone_box", None):
            px1, py1, px2, py2 = res.phone_box
            cv2.rectangle(canvas, (px1, py1), (px2, py2), (50, 50, 255), 2)
            score_txt = f"PHONE: {int(res.phone_score * 100)}%"
            cv2.putText(canvas, score_txt, (px1, max(18, py1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 255), 2)

        # Container / Drinking
        if getattr(res, "container_detected", False) and getattr(res, "container_box", None):
            cx1, cy1, cx2, cy2 = res.container_box
            is_drk = getattr(res, "is_drinking", False)
            color = (255, 220, 0) if is_drk else (230, 180, 50)
            cv2.rectangle(canvas, (cx1, cy1), (cx2, cy2), color, 3 if is_drk else 2)
            lbl = f"{getattr(res, 'container_label', 'CONTAINER').upper()}"
            if is_drk:
                lbl += " [DRINKING!]"
            cv2.putText(canvas, lbl, (cx1, max(18, cy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if is_drk and getattr(res, "mouth_point", None):
                mx, my = res.mouth_point
                cont_top = (int((cx1 + cx2) / 2), cy1)
                cv2.line(canvas, cont_top, (mx, my), (255, 255, 0), 2, cv2.LINE_AA)

    def _draw_study_alert(self, canvas: np.ndarray, text: str, w: int, h: int) -> None:
        banner_w = min(w - 40, len(text) * 14 + 50)
        bx1 = (w - banner_w) // 2
        bx2 = bx1 + banner_w
        by1 = 45
        by2 = 85
        cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (20, 20, 26), -1)
        cv2.rectangle(canvas, (bx1, by1), (bx2, by2), (0, 215, 255), 2)
        cv2.putText(canvas, text, (bx1 + 18, by1 + 27), cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 240, 255), 1, cv2.LINE_AA)


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
        self,
        canvas: np.ndarray,
        state: str,
        mode: str,
        gesture: str,
        confidence: float,
        fps: float,
        w: int,
        study_active: bool = False,
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

        if study_active:
            cv2.putText(canvas, "[STUDY GUARD ON]", (255, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 235, 255), 2, cv2.LINE_AA)

        # Render Middle: Gesture
        if gesture != "none":
            offset_x = 425 if study_active else int(w * 0.42)
            g_text = f"GESTURE: {gesture.upper()} ({int(confidence * 100)}%)"
            cv2.putText(canvas, g_text, (offset_x, 24),
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
