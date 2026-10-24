"""Comprehensive unit tests for the Simple Gesture UX, responsiveness, and performance overhaul."""

import pytest
import time
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    GestureType,
    Handedness,
    IntentType,
    GestureRecognitionResult,
    InteractionMode,
)
from app.gestures.static_detector import StaticGestureDetector
from app.gestures.pinch_engine import PinchEngine, PinchEvent
from app.cursor.cursor_engine import CursorEngine
from app.core.config import PinchConfig, CursorConfig, GestureOSConfig
from app.modes.mouse_mode import MouseMode
from app.modes.media_mode import MediaMode
from app.modes.browser_mode import BrowserMode
from app.modes.presentation_mode import PresentationMode
from app.modes.window_mode import WindowMode
from app.modes.drawing_mode import DrawingMode
from app.ui.gesture_editor import RECOMMENDED_PAIRS


def _make_hand(finger_ext: dict, thumb_tip_y=0.6, wrist_y=0.8, handedness=Handedness.RIGHT, thumb_dist=0.8):
    pts = [Point3D(0.5, 0.5, 0.0) for _ in range(21)]
    pts[0] = Point3D(0.5, wrist_y, 0.0)      # Wrist
    pts[4] = Point3D(0.5, thumb_tip_y, 0.0)  # Thumb tip
    pts[8] = Point3D(0.5, 0.3, 0.0)          # Index tip
    pts[12] = Point3D(0.52, 0.3, 0.0)        # Middle tip
    pts[16] = Point3D(0.6, 0.4, 0.0)         # Ring tip
    pts[20] = Point3D(0.7, 0.5, 0.0)         # Pinky tip

    hand = HandLandmarks(landmarks=pts, handedness=handedness, score=0.95)
    feat = HandFeatures(
        palm_center=Point2D(0.5, 0.6),
        hand_scale=0.3,
        finger_extended=finger_ext,
        finger_curl_angles={"thumb": 160.0, "index": 170.0, "middle": 170.0, "ring": 170.0, "pinky": 170.0},
        thumb_index_dist=thumb_dist,
        thumb_middle_dist=0.8,
        bounding_box=(0.4, 0.3, 0.7, 0.8),
    )
    return hand, feat


def test_thumbs_down_static_detection():
    detector = StaticGestureDetector()
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    # Thumb tip below wrist (larger y in normalized camera coordinates) -> Thumbs Down
    hand, feat = _make_hand(ext, thumb_tip_y=0.85, wrist_y=0.7)
    res = detector.detect(hand, feat)
    assert res.gesture == GestureType.THUMBS_DOWN
    assert res.confidence >= 0.85


def test_mouse_mode_thumbs_up_and_down_scroll():
    cursor = CursorEngine()
    mode = MouseMode(cursor)
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)

    # Thumbs up -> Scroll Up
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent1 = mode.process_gesture(res_up, hand, feat, timestamp=1.0)
    assert intent1 is not None
    assert intent1.intent_type == IntentType.SCROLL_VERTICAL
    assert intent1.params["dy"] > 0

    # Scroll rate limiting: Immediate next call before rate limit interval should return None
    intent_spam = mode.process_gesture(res_up, hand, feat, timestamp=1.02)
    assert intent_spam is None

    # After rate limit interval (e.g. 0.09s later), next scroll should succeed
    intent2 = mode.process_gesture(res_up, hand, feat, timestamp=1.10)
    assert intent2 is not None
    assert intent2.intent_type == IntentType.SCROLL_VERTICAL
    assert intent2.params["dy"] > 0

    # Thumbs down -> Scroll Down
    res_down = GestureRecognitionResult(GestureType.THUMBS_DOWN, 0.95)
    intent_down = mode.process_gesture(res_down, hand, feat, timestamp=1.20)
    assert intent_down is not None
    assert intent_down.intent_type == IntentType.SCROLL_VERTICAL
    assert intent_down.params["dy"] < 0


def test_media_mode_simple_gestures():
    cursor = CursorEngine()
    mode = MediaMode(cursor)
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)

    # Thumbs up -> Volume Up
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent_vup = mode.process_gesture(res_up, hand, feat, timestamp=1.0)
    assert intent_vup is not None
    assert intent_vup.intent_type == IntentType.VOLUME_SET
    assert intent_vup.params["level"] > 0

    # Volume rate limiting: Immediate next frame is suppressed
    intent_vup_spam = mode.process_gesture(res_up, hand, feat, timestamp=1.02)
    assert intent_vup_spam is None

    # Thumbs down -> Volume Down (after rate-limit interval)
    res_down = GestureRecognitionResult(GestureType.THUMBS_DOWN, 0.95)
    intent_vdown = mode.process_gesture(res_down, hand, feat, timestamp=1.10)
    assert intent_vdown is not None
    assert intent_vdown.intent_type == IntentType.VOLUME_SET
    assert intent_vdown.params["level"] < intent_vup.params["level"]

    # Peace (Two Fingers) -> Play / Pause
    res_peace = GestureRecognitionResult(GestureType.PEACE, 0.95)
    intent_play = mode.process_gesture(res_peace, hand, feat, timestamp=1.20)
    assert intent_play is not None
    assert intent_play.intent_type == IntentType.MEDIA_PLAY_PAUSE


def test_browser_mode_simple_gestures():
    cursor = CursorEngine()
    mode = BrowserMode(cursor)
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    hand_r, feat_r = _make_hand(ext, handedness=Handedness.RIGHT)
    hand_l, feat_l = _make_hand(ext, handedness=Handedness.LEFT)

    # Thumbs up -> Scroll Up
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent_up = mode.process_gesture(res_up, hand_r, feat_r, timestamp=1.0)
    assert intent_up is not None
    assert intent_up.intent_type == IntentType.SCROLL_VERTICAL
    assert intent_up.params["dy"] > 0

    # Thumbs down -> Scroll Down
    res_down = GestureRecognitionResult(GestureType.THUMBS_DOWN, 0.95)
    intent_down = mode.process_gesture(res_down, hand_r, feat_r, timestamp=1.10)
    assert intent_down is not None
    assert intent_down.intent_type == IntentType.SCROLL_VERTICAL
    assert intent_down.params["dy"] < 0

    # Peace -> New Tab
    res_peace = GestureRecognitionResult(GestureType.PEACE, 0.95)
    intent_tab = mode.process_gesture(res_peace, hand_r, feat_r, timestamp=1.20)
    assert intent_tab is not None
    assert intent_tab.intent_type == IntentType.BROWSER_NEW_TAB

    # Right Hand Fist -> Back
    res_fist = GestureRecognitionResult(GestureType.FIST, 0.95)
    intent_back = mode.process_gesture(res_fist, hand_r, feat_r, timestamp=1.30)
    assert intent_back is not None
    assert intent_back.intent_type == IntentType.BROWSER_BACK

    # Left Hand Fist -> Forward (after 0.40s debounce)
    intent_fwd = mode.process_gesture(res_fist, hand_l, feat_l, timestamp=1.75)
    assert intent_fwd is not None
    assert intent_fwd.intent_type == IntentType.BROWSER_FORWARD


def test_presentation_mode_simple_gestures():
    cursor = CursorEngine()
    mode = PresentationMode(cursor)
    ext_open = {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    hand, feat = _make_hand(ext_open)

    # Open Palm -> Laser pointer MOUSE_MOVE
    res_palm = GestureRecognitionResult(GestureType.OPEN_PALM, 0.95)
    intent_pointer = mode.process_gesture(res_palm, hand, feat, timestamp=1.0)
    assert intent_pointer is not None
    assert intent_pointer.intent_type == IntentType.MOUSE_MOVE

    # Thumbs Up -> Start Presentation
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent_start = mode.process_gesture(res_up, hand, feat, timestamp=1.10)
    assert intent_start is not None
    assert intent_start.intent_type == IntentType.PRESENTATION_START

    # Fist -> Stop presentation
    res_fist = GestureRecognitionResult(GestureType.FIST, 0.95)
    intent_stop = mode.process_gesture(res_fist, hand, feat, timestamp=1.20)
    assert intent_stop is not None
    assert intent_stop.intent_type == IntentType.PRESENTATION_STOP


def test_window_mode_simple_gestures():
    cursor = CursorEngine()
    mode = WindowMode(cursor)
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)

    # Thumbs Up -> Maximize
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent_max = mode.process_gesture(res_up, hand, feat, timestamp=1.0)
    assert intent_max is not None
    assert intent_max.intent_type == IntentType.WINDOW_MAXIMIZE

    # Thumbs Down -> Minimize
    res_down = GestureRecognitionResult(GestureType.THUMBS_DOWN, 0.95)
    intent_min = mode.process_gesture(res_down, hand, feat, timestamp=1.10)
    assert intent_min is not None
    assert intent_min.intent_type == IntentType.WINDOW_MINIMIZE


def test_drawing_mode_simple_gestures():
    cursor = CursorEngine()
    mode = DrawingMode(cursor)
    ext = {"thumb": True, "index": False, "middle": False, "ring": False, "pinky": False}
    hand, feat = _make_hand(ext)

    # Thumbs Up -> Undo
    res_up = GestureRecognitionResult(GestureType.THUMBS_UP, 0.95)
    intent_undo = mode.process_gesture(res_up, hand, feat, timestamp=1.0)
    assert intent_undo is not None
    assert intent_undo.intent_type == IntentType.DRAW_UNDO

    # Thumbs Down -> Redo (after 0.35s debounce interval)
    res_down = GestureRecognitionResult(GestureType.THUMBS_DOWN, 0.95)
    intent_redo = mode.process_gesture(res_down, hand, feat, timestamp=1.40)
    assert intent_redo is not None
    assert intent_redo.intent_type == IntentType.DRAW_REDO

    # Peace -> Brush vs Eraser tool switch
    was_eraser = mode.is_eraser
    res_peace = GestureRecognitionResult(GestureType.PEACE, 0.95)
    mode.process_gesture(res_peace, hand, feat, timestamp=1.80)
    assert mode.is_eraser != was_eraser

    # Open Palm -> Draw Stroke
    ext_palm = {"thumb": True, "index": True, "middle": True, "ring": True, "pinky": True}
    hand_p, feat_p = _make_hand(ext_palm)
    res_palm = GestureRecognitionResult(GestureType.OPEN_PALM, 0.95)
    intent_draw = mode.process_gesture(res_palm, hand_p, feat_p, timestamp=2.0)
    assert intent_draw is not None
    assert intent_draw.intent_type == IntentType.DRAW_STROKE


def test_movement_based_pinch_drag():
    engine = PinchEngine(PinchConfig(movement_drag_threshold=0.03))

    # 1. Close pinch at position (0.5, 0.5)
    ev1 = engine.update(0.04, 1.0, cursor_pos=(0.5, 0.5))
    assert not engine.is_dragging

    # 2. Slight jitter (movement < threshold) remains in pinch, not drag
    ev2 = engine.update(0.04, 1.05, cursor_pos=(0.51, 0.51))
    assert not engine.is_dragging

    # 3. Clear movement (movement >= 0.03) immediately enters DRAG_START without waiting for hold timer!
    ev3 = engine.update(0.04, 1.08, cursor_pos=(0.55, 0.55))
    assert ev3 == PinchEvent.DRAG_START
    assert engine.is_dragging

    # 4. Continues dragging
    ev4 = engine.update(0.04, 1.10, cursor_pos=(0.58, 0.58))
    assert ev4 == PinchEvent.DRAG_MOVE

    # 5. Release pinch (distance opens to 0.50 >= release_threshold 0.36) -> DRAG_END
    ev5 = engine.update(0.50, 1.15, cursor_pos=(0.58, 0.58))
    assert ev5 == PinchEvent.DRAG_END
    assert not engine.is_dragging


def test_hand_loss_drag_release():
    cursor = CursorEngine()
    mode = MouseMode(cursor)
    hand, feat = _make_hand({}, thumb_dist=0.03)

    # Force a pinch drag in progress
    mode.pinch_engine.update(0.02, 1.0, cursor_pos=(0.5, 0.5))
    mode.pinch_engine.update(0.02, 1.05, cursor_pos=(0.6, 0.6))
    assert mode.pinch_engine.is_dragging

    # When hand is lost, handle_hand_lost must produce DRAG_END safely
    lost_intent = mode.handle_hand_lost(timestamp=1.10)
    assert lost_intent is not None
    assert lost_intent.intent_type == IntentType.DRAG_END
    assert not mode.pinch_engine.is_dragging

    # Calling again when already cleared returns None
    assert mode.handle_hand_lost(timestamp=1.15) is None


def test_responsive_presets_differentiation():
    cursor = CursorEngine()

    # Apply FAST preset
    cursor.set_smoothing_level("Fast")
    fast_cutoff = cursor.x_filter.min_cutoff
    fast_beta = cursor.x_filter.beta
    fast_dead_zone = cursor.filter_config.dead_zone_radius

    # Apply BALANCED preset
    cursor.set_smoothing_level("Balanced")
    bal_cutoff = cursor.x_filter.min_cutoff
    bal_beta = cursor.x_filter.beta
    bal_dead_zone = cursor.filter_config.dead_zone_radius

    # Apply PRECISE preset
    cursor.set_smoothing_level("Precise")
    prec_cutoff = cursor.x_filter.min_cutoff
    prec_beta = cursor.x_filter.beta
    prec_dead_zone = cursor.filter_config.dead_zone_radius

    # Verify they have genuinely different values
    assert fast_cutoff > bal_cutoff > prec_cutoff
    assert fast_beta > bal_beta > prec_beta
    assert prec_dead_zone > bal_dead_zone >= fast_dead_zone


def test_smart_gesture_mapping_recommendations():
    assert "🖐 Open Hand" in RECOMMENDED_PAIRS
    assert "Move Cursor" in RECOMMENDED_PAIRS["🖐 Open Hand"]
    assert "👍 Thumbs Up" in RECOMMENDED_PAIRS
    assert "Vertical Scroll (Up)" in RECOMMENDED_PAIRS["👍 Thumbs Up"]
    assert "👎 Thumbs Down" in RECOMMENDED_PAIRS
    assert "Vertical Scroll (Down)" in RECOMMENDED_PAIRS["👎 Thumbs Down"]
    assert "✌ Two Fingers (V-Shape)" in RECOMMENDED_PAIRS
    assert "Play / Pause / Secondary" in RECOMMENDED_PAIRS["✌ Two Fingers (V-Shape)"]
