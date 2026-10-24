"""MediaPipe Tasks vision detector for Book, Phone, Water Bottle, Cup, and Face."""

from __future__ import annotations
import os
import math
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any


@dataclass
class StudyDetectionResult:
    """Consolidated vision results for study activity monitoring."""
    book_detected: bool = False
    book_box: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    book_score: float = 0.0

    phone_detected: bool = False
    phone_box: Optional[Tuple[int, int, int, int]] = None
    phone_score: float = 0.0

    container_detected: bool = False
    container_box: Optional[Tuple[int, int, int, int]] = None
    container_score: float = 0.0
    container_label: str = ""

    face_detected: bool = False
    face_box: Optional[Tuple[int, int, int, int]] = None
    mouth_point: Optional[Tuple[int, int]] = None

    is_drinking: bool = False
    drinking_confidence: float = 0.0

    timestamp: float = 0.0


class StudyVisionDetector:
    """Wraps MediaPipe ObjectDetector and BlazeFace for multi-modal study & distraction detection."""

    BOOK_LABELS = {"book"}
    PHONE_LABELS = {"cell phone", "phone", "mobile"}
    CONTAINER_LABELS = {"bottle", "cup", "wine glass"}

    def __init__(
        self,
        object_model_path: str = "models/efficientdet_lite0.tflite",
        face_model_path: str = "models/blaze_face_short_range.tflite",
        min_object_confidence: float = 0.28,
        min_face_confidence: float = 0.40,
    ) -> None:
        self.min_object_confidence = min_object_confidence
        self.min_face_confidence = min_face_confidence

        self.object_model_path = self._resolve_model_path(object_model_path, "efficientdet_lite0.tflite")
        self.face_model_path = self._resolve_model_path(face_model_path, "blaze_face_short_range.tflite")

        self._obj_detector: Optional[vision.ObjectDetector] = None
        self._face_detector: Optional[vision.FaceDetector] = None

        self._init_models()

    def _resolve_model_path(self, target_path: str, filename: str) -> str:
        """Finds model path across project subdirectories and ResourceManager."""
        if os.path.exists(target_path):
            return os.path.abspath(target_path)

        try:
            from app.core.resources import get_resource_manager
            rm = get_resource_manager()
            if "efficientdet" in filename:
                cand = rm.get_object_model_path()
            else:
                cand = rm.get_face_model_path()
            if cand.exists():
                return str(cand)
        except Exception:
            pass

        candidates = [
            os.path.abspath(os.path.join(os.getcwd(), target_path)),
            os.path.abspath(os.path.join(os.getcwd(), "models", filename)),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", filename)),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

        return target_path

    def _init_models(self) -> None:
        """Initializes MediaPipe Task detectors."""
        try:
            if os.path.exists(self.object_model_path):
                obj_opts = vision.ObjectDetectorOptions(
                    base_options=python.BaseOptions(model_asset_path=self.object_model_path),
                    score_threshold=self.min_object_confidence,
                    max_results=8,
                )
                self._obj_detector = vision.ObjectDetector.create_from_options(obj_opts)
            else:
                print(f"[StudyVisionDetector] Warning: Object model not found at {self.object_model_path}")
        except Exception as e:
            print(f"[StudyVisionDetector] Failed to init ObjectDetector: {e}")

        try:
            if os.path.exists(self.face_model_path):
                face_opts = vision.FaceDetectorOptions(
                    base_options=python.BaseOptions(model_asset_path=self.face_model_path),
                    min_detection_confidence=self.min_face_confidence,
                )
                self._face_detector = vision.FaceDetector.create_from_options(face_opts)
            else:
                print(f"[StudyVisionDetector] Warning: Face model not found at {self.face_model_path}")
        except Exception as e:
            print(f"[StudyVisionDetector] Failed to init FaceDetector: {e}")

    def detect(self, bgr_frame: np.ndarray) -> StudyDetectionResult:
        """Processes a single BGR frame and returns all detected study & hydration cues."""
        h, w = bgr_frame.shape[:2]
        result = StudyDetectionResult()

        if self._obj_detector is None and self._face_detector is None:
            return result

        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # 1. Face Detection
        if self._face_detector is not None:
            try:
                face_res = self._face_detector.detect(mp_img)
                if face_res.detections:
                    best_face = face_res.detections[0]
                    bb = best_face.bounding_box
                    fx1 = max(0, bb.origin_x)
                    fy1 = max(0, bb.origin_y)
                    fx2 = min(w, bb.origin_x + bb.width)
                    fy2 = min(h, bb.origin_y + bb.height)
                    result.face_detected = True
                    result.face_box = (fx1, fy1, fx2, fy2)

                    # Extract mouth center (index 3 in BlazeFace 6 keypoints)
                    if best_face.keypoints and len(best_face.keypoints) > 3:
                        mk = best_face.keypoints[3]
                        mx = int(mk.x * w)
                        my = int(mk.y * h)
                        result.mouth_point = (mx, my)
                    else:
                        # Fallback mouth estimate (center-bottom of face box)
                        result.mouth_point = (int((fx1 + fx2) / 2), int(fy1 + 0.8 * (fy2 - fy1)))
            except Exception as e:
                pass

        # 2. Object Detection (Book, Cell Phone, Bottle, Cup)
        if self._obj_detector is not None:
            try:
                obj_res = self._obj_detector.detect(mp_img)
                for det in obj_res.detections:
                    if not det.categories:
                        continue
                    cat = det.categories[0]
                    label = cat.category_name.lower().strip()
                    score = cat.score

                    bb = det.bounding_box
                    x1 = max(0, bb.origin_x)
                    y1 = max(0, bb.origin_y)
                    x2 = min(w, bb.origin_x + bb.width)
                    y2 = min(h, bb.origin_y + bb.height)
                    box = (x1, y1, x2, y2)

                    # Book
                    if label in self.BOOK_LABELS and score > result.book_score:
                        result.book_detected = True
                        result.book_box = box
                        result.book_score = score

                    # Phone
                    elif label in self.PHONE_LABELS and score > result.phone_score:
                        result.phone_detected = True
                        result.phone_box = box
                        result.phone_score = score

                    # Bottle / Cup
                    elif label in self.CONTAINER_LABELS and score > result.container_score:
                        result.container_detected = True
                        result.container_box = box
                        result.container_score = score
                        result.container_label = label
            except Exception as e:
                pass

        # 3. Analyze Drinking Action
        if result.container_detected and result.container_box is not None:
            cx1, cy1, cx2, cy2 = result.container_box
            cont_center_x = (cx1 + cx2) / 2
            cont_top_y = cy1
            cont_w = cx2 - cx1
            cont_h = cy2 - cy1

            if result.face_detected and result.face_box is not None:
                fx1, fy1, fx2, fy2 = result.face_box
                mouth_x, mouth_y = result.mouth_point or ((fx1 + fx2) / 2, fy1 + 0.8 * (fy2 - fy1))

                # Distance from top of bottle/cup to mouth
                dx = abs(cont_center_x - mouth_x)
                dy = abs(cont_top_y - mouth_y)
                dist_norm = math.hypot(dx / w, dy / h)

                # Check overlap with lower half of face (mouth region)
                overlap_x = max(0, min(cx2, fx2) - max(cx1, fx1))
                overlap_y = max(0, min(cy2, fy2) - max(cy1, fy1 + 0.3 * (fy2 - fy1)))
                has_mouth_overlap = (overlap_x > 0.2 * cont_w) and (overlap_y > 0)

                # Drinking condition: container top is near mouth OR overlaps lower face
                if dist_norm < 0.16 or (dx < 0.8 * cont_w and dy < 0.8 * cont_h) or has_mouth_overlap:
                    result.is_drinking = True
                    result.drinking_confidence = min(1.0, result.container_score + 0.2)
            else:
                # Fallback if face is partially occluded by large bottle:
                # If bottle is positioned high in the camera view (upper 45%)
                if cont_top_y < 0.45 * h:
                    result.is_drinking = True
                    result.drinking_confidence = result.container_score * 0.85

        return result

    def close(self) -> None:
        """Closes and releases MediaPipe detectors from memory."""
        if self._obj_detector is not None:
            try:
                self._obj_detector.close()
            except Exception:
                pass
            self._obj_detector = None
        if self._face_detector is not None:
            try:
                self._face_detector.close()
            except Exception:
                pass
            self._face_detector = None
