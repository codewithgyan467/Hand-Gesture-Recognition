"""Lightweight Scikit-Learn custom ML gesture classifier with training, evaluation, and export."""

from __future__ import annotations
import os
import json
import joblib
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from app.core.types import HandLandmarks, HandFeatures
from app.diagnostics.logger import get_logger

logger = get_logger("ml_classifier")


class CustomMLGestureClassifier:
    """Trains and executes lightweight ML classifiers for custom, personalized, or ambiguous gestures."""

    def __init__(self, model_path: str = "models/custom_gesture_model.joblib") -> None:
        self.model_path = model_path
        self._model: Optional[RandomForestClassifier] = None
        self._labels: List[str] = []
        self._is_loaded = False
        self.load_model()

    @property
    def is_ready(self) -> bool:
        return self._is_loaded and self._model is not None

    def load_model(self) -> bool:
        if not os.path.isfile(self.model_path):
            return False
        try:
            bundle = joblib.load(self.model_path)
            self._model = bundle["model"]
            self._labels = bundle["labels"]
            self._is_loaded = True
            logger.info(f"Loaded custom ML gesture model with labels: {self._labels}")
            return True
        except Exception as e:
            logger.warning(f"Could not load custom ML model: {e}")
            self._is_loaded = False
            return False

    def predict(self, landmarks: HandLandmarks, features: HandFeatures) -> Tuple[Optional[str], float]:
        """Predicts custom gesture label and confidence score from hand landmarks."""
        if not self.is_ready:
            return (None, 0.0)

        cx = features.palm_center.x
        cy = features.palm_center.y
        scale = features.hand_scale

        vector = []
        for lm in landmarks.landmarks:
            norm_x = (lm.x - cx) / scale
            norm_y = (lm.y - cy) / scale
            norm_z = lm.z / scale
            vector.extend([norm_x, norm_y, norm_z])

        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            vector.append(features.finger_curl_angles.get(finger, 0.0) / 180.0)

        x_arr = np.array(vector, dtype=np.float32).reshape(1, -1)

        try:
            probs = self._model.predict_proba(x_arr)[0]
            best_idx = np.argmax(probs)
            confidence = float(probs[best_idx])
            label = self._labels[best_idx]
            return (label, confidence)
        except Exception as e:
            logger.error(f"Error during ML prediction: {e}")
            return (None, 0.0)

    def train_from_dataset(self, dataset_dir: str = "datasets") -> Dict[str, Any]:
        """Loads collected samples, trains Random Forest model, computes confusion matrix and metrics."""
        x_data: List[List[float]] = []
        y_data: List[str] = []

        if not os.path.isdir(dataset_dir):
            raise ValueError(f"Dataset directory '{dataset_dir}' does not exist.")

        classes = [d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))]
        if len(classes) < 2:
            raise ValueError(f"Need at least 2 gesture classes to train a model. Found: {classes}")

        for label in classes:
            folder = os.path.join(dataset_dir, label)
            sample_files = [f for f in os.listdir(folder) if f.endswith(".json")]
            for f in sample_files:
                path = os.path.join(folder, f)
                with open(path, "r", encoding="utf-8") as s_file:
                    content = json.load(s_file)
                    x_data.append(content["feature_vector"])
                    y_data.append(label)

        if len(x_data) < 10:
            raise ValueError(f"Insufficient samples (minimum 10 required, got {len(x_data)}).")

        x_np = np.array(x_data, dtype=np.float32)
        y_np = np.array(y_data)

        # Train / validation split
        x_train, x_val, y_train, y_val = train_test_split(
            x_np, y_np, test_size=0.25, random_state=42, stratify=y_np
        )

        clf = RandomForestClassifier(n_estimators=60, max_depth=12, random_state=42)
        clf.fit(x_train, y_train)

        # Evaluation
        y_pred = clf.predict(x_val)
        acc = float(accuracy_score(y_val, y_pred))
        conf_mat = confusion_matrix(y_val, y_pred, labels=clf.classes_).tolist()

        # Save bundle
        os.makedirs(os.path.dirname(os.path.abspath(self.model_path)), exist_ok=True)
        bundle = {
            "model": clf,
            "labels": list(clf.classes_),
            "accuracy": acc,
        }
        joblib.dump(bundle, self.model_path)

        self._model = clf
        self._labels = list(clf.classes_)
        self._is_loaded = True

        logger.info(f"Custom ML model trained successfully. Validation Accuracy: {acc:.4f}")
        return {
            "accuracy": acc,
            "classes": list(clf.classes_),
            "confusion_matrix": conf_mat,
            "total_samples": len(x_data),
        }
