"""Unit tests for TwoHandCoordinator role assignment, dual gestures, and safety cutoff."""

import pytest
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    GestureType,
    Handedness,
    IntentType,
    GestureRecognitionResult,
)
from app.gestures.two_hand_engine import TwoHandCoordinator


def _make_hand(handedness: Handedness, palm_x: float, palm_y: float = 0.5, gesture: GestureType = GestureType.NONE):
    pts = [Point3D(palm_x, palm_y, 0.0) for _ in range(21)]
    hand = HandLandmarks(landmarks=pts, handedness=handedness, score=0.95)
    feat = HandFeatures(
        palm_center=Point2D(palm_x, palm_y),
        hand_scale=0.3,
        finger_extended={"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True},
        finger_curl_angles={"thumb": 160.0, "index": 170.0, "middle": 170.0, "ring": 170.0, "pinky": 170.0},
        thumb_index_dist=0.8,
        thumb_middle_dist=0.8,
        bounding_box=(palm_x - 0.1, palm_y - 0.1, palm_x + 0.1, palm_y + 0.1),
    )
    res = GestureRecognitionResult(
        gesture=gesture,
        confidence=0.95,
        hand_features=feat,
        handedness=handedness,
        raw_landmarks=hand,
        timestamp=1.0,
    )
    return hand, feat, res


def test_two_hand_role_assignment():
    coord = TwoHandCoordinator()

    # Single right hand -> acts as pointer hand
    hand_r, _, _ = _make_hand(Handedness.RIGHT, 0.6)
    roles = coord.assign_roles([hand_r])
    assert roles["pointer_hand"] == hand_r
    assert roles["command_hand"] is None

    # Two hands: Right and Left
    hand_l, _, _ = _make_hand(Handedness.LEFT, 0.3)
    roles2 = coord.assign_roles([hand_r, hand_l])
    assert roles2["pointer_hand"] == hand_r
    assert roles2["command_hand"] == hand_l


def test_two_hands_moving_apart_maximize():
    coord = TwoHandCoordinator()

    # Initial frame: distance = 0.3
    h1_a, f1_a, r1_a = _make_hand(Handedness.RIGHT, 0.45)
    h2_a, f2_a, r2_a = _make_hand(Handedness.LEFT, 0.15)
    intent1 = coord.process_hands([(h1_a, f1_a, r1_a), (h2_a, f2_a, r2_a)], timestamp=1.0)
    assert intent1 is None

    # Next frame at t=1.8 (after rate limit): hands move apart to distance = 0.55 (delta = +0.25 > 0.12)
    h1_b, f1_b, r1_b = _make_hand(Handedness.RIGHT, 0.65)
    h2_b, f2_b, r2_b = _make_hand(Handedness.LEFT, 0.10)
    intent2 = coord.process_hands([(h1_b, f1_b, r1_b), (h2_b, f2_b, r2_b)], timestamp=1.8)
    assert intent2 is not None
    assert intent2.intent_type == IntentType.WINDOW_MAXIMIZE
