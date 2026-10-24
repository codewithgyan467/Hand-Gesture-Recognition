"""Comprehensive unit tests for all interaction modes and ModeManager lifecycle."""

import os
import pytest
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    GestureType,
    Handedness,
    IntentType,
    InteractionMode,
    GestureRecognitionResult,
)
from app.cursor.cursor_engine import CursorEngine
from app.modes.media_mode import MediaMode
from app.modes.browser_mode import BrowserMode
from app.modes.presentation_mode import PresentationMode
from app.modes.window_mode import WindowMode
from app.modes.drawing_mode import DrawingMode
from app.modes.mode_manager import ModeManager


def _make_dummy_hand(finger_ext=None, thumb_index_dist=0.8, thumb_middle_dist=0.8, index_x=0.5, index_y=0.4):
    if finger_ext is None:
        finger_ext = {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    pts = [Point3D(0.5, 0.5, 0.0) for _ in range(21)]
    pts[0] = Point3D(0.5, 0.8, 0.0)
    pts[4] = Point3D(0.4, 0.6, 0.0)
    pts[8] = Point3D(index_x, index_y, 0.0)
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


def test_media_mode_swipes_and_playpause():
    engine = CursorEngine()
    mode = MediaMode(engine)
    hand, feat = _make_dummy_hand()

    # Next track (Swipe Right)
    res_next = GestureRecognitionResult(gesture=GestureType.SWIPE_RIGHT, confidence=0.92, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    intent = mode.process_gesture(res_next, hand, feat, timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.MEDIA_NEXT

    # Previous track (Swipe Left)
    res_prev = GestureRecognitionResult(gesture=GestureType.SWIPE_LEFT, confidence=0.91, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.1)
    intent = mode.process_gesture(res_prev, hand, feat, timestamp=1.1)
    assert intent is not None
    assert intent.intent_type == IntentType.MEDIA_PREV

    # Play / Pause (Open Palm)
    res_pause = GestureRecognitionResult(gesture=GestureType.OPEN_PALM, confidence=0.95, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.2)
    intent = mode.process_gesture(res_pause, hand, feat, timestamp=1.2)
    assert intent is not None
    assert intent.intent_type == IntentType.MEDIA_PLAY_PAUSE


def test_media_mode_continuous_volume():
    engine = CursorEngine()
    mode = MediaMode(engine)
    # Hand with extended thumb and index
    ext = {"thumb": True, "index": True, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_dummy_hand(finger_ext=ext, thumb_index_dist=0.68)

    res = GestureRecognitionResult(gesture=GestureType.NONE, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    intent = mode.process_gesture(res, hand, feat, timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.VOLUME_SET
    assert "level" in intent.params
    assert 0.0 <= intent.params["level"] <= 100.0


def test_browser_mode_navigation():
    engine = CursorEngine()
    mode = BrowserMode(engine)
    hand, feat = _make_dummy_hand()

    # Back
    res_back = GestureRecognitionResult(gesture=GestureType.SWIPE_LEFT, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    assert mode.process_gesture(res_back, hand, feat, timestamp=1.0).intent_type == IntentType.BROWSER_BACK

    # Forward
    res_fwd = GestureRecognitionResult(gesture=GestureType.SWIPE_RIGHT, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.1)
    assert mode.process_gesture(res_fwd, hand, feat, timestamp=1.1).intent_type == IntentType.BROWSER_FORWARD

    # New Tab (Peace)
    res_tab = GestureRecognitionResult(gesture=GestureType.PEACE, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.2)
    assert mode.process_gesture(res_tab, hand, feat, timestamp=1.2).intent_type == IntentType.BROWSER_NEW_TAB


def test_presentation_mode_controls():
    engine = CursorEngine()
    mode = PresentationMode(engine)
    hand, feat = _make_dummy_hand()

    # Next Slide
    res_next = GestureRecognitionResult(gesture=GestureType.SWIPE_RIGHT, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    assert mode.process_gesture(res_next, hand, feat, timestamp=1.0).intent_type == IntentType.PRESENTATION_NEXT

    # Start presentation (Thumbs Up)
    res_start = GestureRecognitionResult(gesture=GestureType.THUMBS_UP, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.1)
    assert mode.process_gesture(res_start, hand, feat, timestamp=1.1).intent_type == IntentType.PRESENTATION_START

    # Laser pointer (Pointer finger)
    res_ptr = GestureRecognitionResult(gesture=GestureType.POINTER, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.2)
    assert mode.process_gesture(res_ptr, hand, feat, timestamp=1.2).intent_type == IntentType.MOUSE_MOVE


def test_window_mode_controls():
    engine = CursorEngine()
    mode = WindowMode(engine)
    hand, feat = _make_dummy_hand()

    # Next Window (Alt+Tab)
    res_next = GestureRecognitionResult(gesture=GestureType.SWIPE_RIGHT, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    assert mode.process_gesture(res_next, hand, feat, timestamp=1.0).intent_type == IntentType.WINDOW_NEXT

    # Maximize
    res_max = GestureRecognitionResult(gesture=GestureType.SWIPE_UP, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.1)
    assert mode.process_gesture(res_max, hand, feat, timestamp=1.1).intent_type == IntentType.WINDOW_MAXIMIZE

    # Minimize
    res_min = GestureRecognitionResult(gesture=GestureType.SWIPE_DOWN, confidence=0.9, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.2)
    assert mode.process_gesture(res_min, hand, feat, timestamp=1.2).intent_type == IntentType.WINDOW_MINIMIZE


def test_drawing_mode_virtual_canvas(tmp_path):
    engine = CursorEngine()
    mode = DrawingMode(engine, canvas_width=640, canvas_height=480)
    hand, feat = _make_dummy_hand()

    # Draw a stroke with POINTER
    res_draw = GestureRecognitionResult(gesture=GestureType.POINTER, confidence=0.95, hand_features=feat, handedness=Handedness.RIGHT, raw_landmarks=hand, timestamp=1.0)
    intent = mode.process_gesture(res_draw, hand, feat, timestamp=1.0)
    assert intent is not None
    assert intent.intent_type == IntentType.DRAW_STROKE
    assert len(mode.strokes) == 1

    # Undo
    assert mode.undo() is True
    assert len(mode.strokes) == 0

    # Redo
    assert mode.redo() is True
    assert len(mode.strokes) == 1

    # Export
    out_file = str(tmp_path / "test_canvas.png")
    assert mode.export_canvas(out_file) is True
    assert os.path.exists(out_file)

    # Clear
    mode.clear_canvas()
    assert len(mode.strokes) == 0


def test_mode_manager_switching_and_properties():
    engine = CursorEngine()
    mgr = ModeManager(engine)

    assert mgr.current_mode_type == InteractionMode.MOUSE
    assert mgr.current_mode_name == "Mouse"

    # Switch to Media
    assert mgr.switch_to_mode(InteractionMode.MEDIA) is True
    assert mgr.current_mode_type == InteractionMode.MEDIA

    # Cycle next mode
    next_m = mgr.cycle_next_mode()
    assert next_m == InteractionMode.BROWSER
    assert mgr.current_mode_type == InteractionMode.BROWSER
