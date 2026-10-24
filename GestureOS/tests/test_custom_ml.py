"""Unit tests for CustomMLGestureClassifier and GestureDatasetCollector."""

import os
import shutil
import pytest
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    Handedness,
)
from app.gestures.dataset_collector import GestureDatasetCollector
from app.gestures.ml_classifier import CustomMLGestureClassifier


def _make_hand(x_offset: float = 0.0):
    pts = [Point3D(0.5 + x_offset, 0.5, 0.0) for _ in range(21)]
    hand = HandLandmarks(landmarks=pts, handedness=Handedness.RIGHT, score=0.95)
    feat = HandFeatures(
        palm_center=Point2D(0.5 + x_offset, 0.5),
        hand_scale=0.3,
        finger_extended={"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True},
        finger_curl_angles={"thumb": 160.0, "index": 170.0, "middle": 170.0, "ring": 170.0, "pinky": 170.0},
        thumb_index_dist=0.8,
        thumb_middle_dist=0.8,
        bounding_box=(0.4 + x_offset, 0.4, 0.6 + x_offset, 0.6),
    )
    return hand, feat


def test_dataset_collector_and_ml_classifier(tmp_path):
    dataset_dir = str(tmp_path / "datasets")
    model_path = str(tmp_path / "test_model.joblib")

    collector = GestureDatasetCollector(dataset_root=dataset_dir)

    # 1. Collect samples for "gesture_a"
    collector.start_collecting("gesture_a")
    for i in range(12):
        hand, feat = _make_hand(x_offset=0.01 * i)
        assert collector.record_sample(hand, feat) is True
    collector.stop_collecting()

    # 2. Collect samples for "gesture_b"
    collector.start_collecting("gesture_b")
    for i in range(12):
        hand, feat = _make_hand(x_offset=-0.05 * i)
        assert collector.record_sample(hand, feat) is True
    collector.stop_collecting()

    counts = collector.get_sample_counts()
    assert counts["gesture_a"] == 12
    assert counts["gesture_b"] == 12

    # 3. Train ML Classifier
    clf = CustomMLGestureClassifier(model_path=model_path)
    metrics = clf.train_from_dataset(dataset_dir=dataset_dir)

    assert clf.is_ready is True
    assert "accuracy" in metrics
    assert "confusion_matrix" in metrics
    assert set(metrics["classes"]) == {"gesture_a", "gesture_b"}
    assert metrics["total_samples"] == 24

    # 4. Predict
    test_hand, test_feat = _make_hand(x_offset=0.01)
    label, conf = clf.predict(test_hand, test_feat)
    assert label in ("gesture_a", "gesture_b")
    assert 0.0 <= conf <= 1.0
