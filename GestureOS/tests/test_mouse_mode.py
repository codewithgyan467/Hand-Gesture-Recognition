"""Unit tests for MouseMode natural hand tracking, clicks, scroll, and fist pause."""

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
from app.cursor.cursor_engine import CursorEngine
from app.modes.mouse_mode import MouseMode
from app.core.config import PinchConfig, CursorConfig, ActiveRegionConfig


def _make_hand(finger_ext: dict, thumb_index_dist=0.8, thumb_middle_dist=0.8, index_x=0.5, index_y=0.4):
    pts = [Point3D(0.5, 0.5, 0.0) for _ in range(21)]
    pts[0] = Point3D(0.5, 0.8, 0.0)
    pts[4] = Point3D(0.4, 0.6, 0.0)
    pts[8] = Point3D(index_x, index_y, 0.0) # Index tip
    pts[12] = Point3D(0.52, 0.3, 0.0)
    pts[16] = Point3D(0.6, 0.4, 0.0)
    pts[20] = Point3D(0.7, 0.5, 0.0)

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


def test_mouse_move_open_palm():
    """Natural open palm movement must generate MOUSE_MOVE intent."""
    cursor_engine = CursorEngine(CursorConfig(screen_width=1920, screen_height=1080))
    mode = MouseMode(cursor_engine)

    ext = {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    hand, feat = _make_hand(ext, index_x=0.5, index_y=0.5)
    res = GestureRecognitionResult(
        gesture=GestureType.OPEN_PALM,
        confidence=0.95,
        hand_features=feat,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand,
        timestamp=1.0,
    )

    intent = mode.process_gesture(res, hand, feat, timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.MOUSE_MOVE
    assert "x" in intent.params and "y" in intent.params
    assert 0 <= intent.params["x"] <= 1920
    assert 0 <= intent.params["y"] <= 1080


def test_mouse_move_pointer_finger():
    """Single pointing index finger must generate MOUSE_MOVE intent."""
    cursor_engine = CursorEngine(CursorConfig(screen_width=1920, screen_height=1080))
    mode = MouseMode(cursor_engine)

    ext = {"thumb": False, "index": True, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext, index_x=0.4, index_y=0.3)
    res = GestureRecognitionResult(
        gesture=GestureType.POINTER,
        confidence=0.92,
        hand_features=feat,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand,
        timestamp=1.0,
    )

    intent = mode.process_gesture(res, hand, feat, timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.MOUSE_MOVE


def test_right_hand_fist_triggers_right_click():
    """Right hand fist/punch must trigger RIGHT_CLICK and subsequent frames pause cursor."""
    cursor_engine = CursorEngine(CursorConfig(screen_width=1920, screen_height=1080))
    mode = MouseMode(cursor_engine)

    ext = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)
    hand.handedness = Handedness.RIGHT
    res = GestureRecognitionResult(
        gesture=GestureType.FIST,
        confidence=0.95,
        hand_features=feat,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand,
        timestamp=1.0,
    )

    # First frame: triggers right click
    intent1 = mode.process_gesture(res, hand, feat, timestamp=1.0)
    assert intent1 is not None
    assert intent1.intent_type == IntentType.RIGHT_CLICK

    # Second frame (held fist): pauses cursor, suppresses repeat clicks
    intent2 = mode.process_gesture(res, hand, feat, timestamp=1.033)
    assert intent2 is None


def test_left_hand_fist_triggers_left_click():
    """Left hand fist/punch must trigger LEFT_CLICK and subsequent frames pause cursor."""
    cursor_engine = CursorEngine(CursorConfig(screen_width=1920, screen_height=1080))
    mode = MouseMode(cursor_engine)

    ext = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)
    hand.handedness = Handedness.LEFT
    res = GestureRecognitionResult(
        gesture=GestureType.FIST,
        confidence=0.95,
        hand_features=feat,
        handedness=Handedness.LEFT,
        raw_landmarks=hand,
        timestamp=1.0,
    )

    # First frame: triggers left click
    intent1 = mode.process_gesture(res, hand, feat, timestamp=1.0)
    assert intent1 is not None
    assert intent1.intent_type == IntentType.LEFT_CLICK

    # Second frame (held fist): pauses cursor
    intent2 = mode.process_gesture(res, hand, feat, timestamp=1.033)
    assert intent2 is None


def test_secondary_hand_punch_click():
    """Pointing with right hand while punching with left hand triggers LEFT_CLICK at cursor position."""
    cursor_engine = CursorEngine(CursorConfig(screen_width=1920, screen_height=1080))
    mode = MouseMode(cursor_engine)

    # Primary hand (Right hand pointing at center)
    ext_point = {"thumb": False, "index": True, "middle": False, "ring": False, "pinky": False}
    hand_r, feat_r = _make_hand(ext_point, index_x=0.5, index_y=0.5)
    hand_r.handedness = Handedness.RIGHT
    res_r = GestureRecognitionResult(
        gesture=GestureType.POINTER,
        confidence=0.92,
        hand_features=feat_r,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand_r,
        timestamp=1.0,
    )

    # Secondary hand (Left hand fist/punch)
    ext_fist = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
    hand_l, feat_l = _make_hand(ext_fist)
    hand_l.handedness = Handedness.LEFT
    res_l = GestureRecognitionResult(
        gesture=GestureType.FIST,
        confidence=0.95,
        hand_features=feat_l,
        handedness=Handedness.LEFT,
        raw_landmarks=hand_l,
        timestamp=1.0,
    )

    intent = mode.process_gesture(
        res_r, hand_r, feat_r, timestamp=1.0,
        secondary_result=res_l, secondary_landmarks=hand_l
    )
    assert intent is not None
    assert intent.intent_type == IntentType.LEFT_CLICK


def test_pinch_click_action():
    """Thumb + index pinch must trigger click intent."""
    pinch_cfg = PinchConfig(pinch_threshold=0.08, release_threshold=0.12)
    cursor_engine = CursorEngine()
    mode = MouseMode(cursor_engine, pinch_config=pinch_cfg)

    ext = {"thumb": True, "index": True, "middle": False, "ring": False, "pinky": False}
    # Pinch engagement (distance <= threshold)
    hand, feat = _make_hand(ext, thumb_index_dist=0.05)
    res = GestureRecognitionResult(
        gesture=GestureType.PINCH_INDEX,
        confidence=0.90,
        hand_features=feat,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand,
        timestamp=1.0,
    )
    mode.process_gesture(res, hand, feat, timestamp=1.0)

    # Release (quick tap < 0.35s)
    hand2, feat2 = _make_hand(ext, thumb_index_dist=0.15)
    res2 = GestureRecognitionResult(
        gesture=GestureType.POINTER,
        confidence=0.90,
        hand_features=feat2,
        handedness=Handedness.RIGHT,
        raw_landmarks=hand2,
        timestamp=1.1,
    )
    intent = mode.process_gesture(res2, hand2, feat2, timestamp=1.1)
    assert intent is not None
    assert intent.intent_type == IntentType.LEFT_CLICK
