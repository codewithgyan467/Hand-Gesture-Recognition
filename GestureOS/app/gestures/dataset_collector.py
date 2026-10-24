"""Dataset collection utility for recording and storing normalized gesture landmark samples."""

from __future__ import annotations
import os
import json
import time
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.types import HandLandmarks, HandFeatures, Point3D
from app.diagnostics.logger import get_logger

logger = get_logger("dataset_collector")


class GestureDatasetCollector:
    """Collects normalized hand landmark vectors for training custom ML models."""

    def __init__(self, dataset_root: str = "datasets") -> None:
        self.dataset_root = dataset_root
        os.makedirs(self.dataset_root, exist_ok=True)
        self._current_gesture_label: Optional[str] = None
        self._samples_collected_in_session = 0

    def start_collecting(self, gesture_label: str) -> str:
        self._current_gesture_label = gesture_label.strip().lower().replace(" ", "_")
        folder = os.path.join(self.dataset_root, self._current_gesture_label)
        os.makedirs(folder, exist_ok=True)
        self._samples_collected_in_session = 0
        logger.info(f"Started dataset recording for gesture: {self._current_gesture_label}")
        return folder

    def record_sample(self, landmarks: HandLandmarks, features: HandFeatures) -> bool:
        """Extracts scale-normalized 63-d feature vector and saves to JSON."""
        if not self._current_gesture_label:
            return False

        # Vector normalized relative to palm center and palm scale
        cx = features.palm_center.x
        cy = features.palm_center.y
        scale = features.hand_scale

        vector = []
        for lm in landmarks.landmarks:
            norm_x = (lm.x - cx) / scale
            norm_y = (lm.y - cy) / scale
            norm_z = lm.z / scale
            vector.extend([norm_x, norm_y, norm_z])

        # Also append 5 joint angles
        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            vector.append(features.finger_curl_angles.get(finger, 0.0) / 180.0)

        # Validate no NaNs
        if np.any(np.isnan(vector)) or np.any(np.isinf(vector)):
            return False

        sample_id = f"sample_{int(time.time() * 1000)}_{self._samples_collected_in_session:04d}"
        folder = os.path.join(self.dataset_root, self._current_gesture_label)
        sample_path = os.path.join(folder, f"{sample_id}.json")

        sample_data = {
            "gesture": self._current_gesture_label,
            "timestamp": time.time(),
            "feature_vector": vector,
            "scale": scale,
        }

        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        self._samples_collected_in_session += 1
        return True

    def get_sample_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        if not os.path.isdir(self.dataset_root):
            return counts
        for entry in os.listdir(self.dataset_root):
            p = os.path.join(self.dataset_root, entry)
            if os.path.isdir(p):
                samples = [f for f in os.listdir(p) if f.endswith(".json")]
                counts[entry] = len(samples)
        return counts

    def stop_collecting(self) -> int:
        count = self._samples_collected_in_session
        label = self._current_gesture_label
        self._current_gesture_label = None
        self._samples_collected_in_session = 0
        logger.info(f"Stopped collecting for {label}. Total samples saved: {count}")
        return count
