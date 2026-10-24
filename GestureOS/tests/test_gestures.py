"""Unit tests for static and dynamic gesture classification."""

import pytest
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    GestureType,
    Handedness,
    IntentType,
)
from app.gestures.static_detector import StaticGestureDetector
from app.gestures.dynamic_detector import DynamicGestureDetector
from app.gestures.two_hand_engine import TwoHandCoordinator
from app.core.config import PinchConfig, GestureValidationConfig


def _make_dummy_hand(finger_ext: dict, thumb_index_dist=0.8, thumb_middle_dist=0.8):
    pts = [Point3D(0.5, 0.5, 0.0) for _ in range(21)]
    # Set wrist and tips
    pts[0] = Point3D(0.5, 0.8, 0.0)
    pts[4] = Point3D(0.4, 0.6, 0.0)  # Thumb tip
    pts[8] = Point3D(0.5, 0.3, 0.0)  # Index tip
    pts[12] = Point3D(0.52, 0.3, 0.0) # Middle tip
    pts[16] = Point3D(0.6, 0.4, 0.0) # Ring tip
    pts[20] = Point3D(0.7, 0.5, 0.0) # Pinky tip

    hand = HandLandmarks(landmarks=pts, handedness=Handedness.RIGHT, score=0.95)
    feat = HandFeatures(
        palm_center=Point2D(0.5, 0.6),
        hand_scale=0.3,
        finger_extended=finger_ext,
        finger_curl_angles={"thumb": 160.0, "index": 170.0, "middle": 170.0, "ring": 170.0, "pinky": 170.0},
        thumb_index_dist=thumb_index_dist,
        thumb_middle_dist=thumb_middle_dist,
        bounding_box=(0.4, 0.3, 0.7, 0.8),
    )
    return hand, feat


def test_static_pointer_detection():
    detector = StaticGestureDetector()
    ext = {"thumb": False, "index": True, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_dummy_hand(ext)
    res = detector.detect(hand, feat)
    assert res.gesture == GestureType.POINTER
    assert res.confidence >= 0.90


def test_static_fist_detection():
    detector = StaticGestureDetector()
    ext = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_dummy_hand(ext)
    res = detector.detect(hand, feat)
    assert res.gesture == GestureType.FIST


def test_static_open_palm_detection():
    detector = StaticGestureDetector()
    ext = {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    hand, feat = _make_dummy_hand(ext)
    res = detector.detect(hand, feat)
    assert res.gesture == GestureType.OPEN_PALM


def test_static_pinch_index_detection():
    detector = StaticGestureDetector()
    ext = {"thumb": True, "index": True, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_dummy_hand(ext, thumb_index_dist=0.18)
    res = detector.detect(hand, feat)
    assert res.gesture == GestureType.PINCH_INDEX


def test_dynamic_swipe_right():
    val_cfg = GestureValidationConfig(swipe_min_velocity=0.3, swipe_min_distance=0.1)
    detector = DynamicGestureDetector(val_cfg, buffer_duration_sec=0.5)
    ext = {"thumb": True, "index": True, "middle": True, "ring": False, "pinky": False}
    hand, feat = _make_dummy_hand(ext)

    # Feed trajectory moving rapidly right: x=0.2 to x=0.7 in 0.2s
    t0 = 1.0
    for i in range(8):
        t = t0 + i * 0.025
        x = 0.20 + (i / 7.0) * 0.50
        y = 0.50
        res = detector.update(Point2D(x, y), feat, hand, timestamp=t)
        if res.gesture != GestureType.NONE:
            break

    assert res.gesture == GestureType.SWIPE_RIGHT
    assert res.confidence >= 0.75


def test_two_hand_dual_fists_emergency():
    coord = TwoHandCoordinator()
    fist_ext = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
    hand1, feat1 = _make_dummy_hand(fist_ext)
    hand2, feat2 = _make_dummy_hand(fist_ext)

    detector = StaticGestureDetector()
    res1 = detector.detect(hand1, feat1)
    res2 = detector.detect(hand2, feat2)

    intent = coord.process_hands([(hand1, feat1, res1), (hand2, feat2, res2)], timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.EMERGENCY_STOP_TRIGGER
