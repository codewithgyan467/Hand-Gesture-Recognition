"""Core domain types, enums, and data models for GestureOS."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict, Any


class HandLandmarkIndex(int, Enum):
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class Handedness(str, Enum):
    LEFT = "Left"
    RIGHT = "Right"
    UNKNOWN = "Unknown"


class GestureType(str, Enum):
    NONE = "none"
    POINTER = "pointer"
    PINCH_INDEX = "pinch_index"
    PINCH_MIDDLE = "pinch_middle"
    PINCH_HOLD = "pinch_hold"
    SCROLL = "scroll"
    FIST = "fist"
    OPEN_PALM = "open_palm"
    DUAL_FISTS = "dual_fists"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PEACE = "peace"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    WAVE = "wave"
    CIRCLE_CW = "circle_cw"
    CIRCLE_CCW = "circle_ccw"
    CUSTOM_ML = "custom_ml"


class GestureState(str, Enum):
    INACTIVE = "inactive"           # Passive mode: webcam tracks, OS actions disabled
    ACTIVATING = "activating"       # User is holding activation gesture (progress towards active)
    ACTIVE = "active"               # Fully armed, listening for gestures
    GESTURE_DETECTED = "detected"   # A raw gesture candidate was recognized
    VALIDATING = "validating"       # Debouncing / consecutive frame confirmation
    EXECUTING = "executing"         # Performing action (e.g., dragging, clicking)
    COOLDOWN = "cooldown"           # Post-action cooldown to prevent flutter
    TRACKING_LOST = "tracking_lost" # Hand lost from field of view
    CAMERA_ERROR = "camera_error"   # Camera hardware disconnected or error
    EMERGENCY_STOP = "emergency_stop" # Hard safety cutoff triggered


class InteractionMode(str, Enum):
    MOUSE = "Mouse"
    MEDIA = "Media"
    BROWSER = "Browser"
    PRESENTATION = "Presentation"
    WINDOW = "Window"
    DRAWING = "Drawing"
    CUSTOM = "Custom"


class IntentType(str, Enum):
    NO_ACTION = "no_action"
    # Mouse intents
    MOUSE_MOVE = "mouse_move"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    DRAG_START = "drag_start"
    DRAG_MOVE = "drag_move"
    DRAG_END = "drag_end"
    SCROLL_VERTICAL = "scroll_vertical"
    SCROLL_HORIZONTAL = "scroll_horizontal"
    # Volume intents
    VOLUME_SET = "volume_set"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    # Media intents
    MEDIA_PLAY_PAUSE = "media_play_pause"
    MEDIA_NEXT = "media_next"
    MEDIA_PREV = "media_prev"
    # Browser intents
    BROWSER_BACK = "browser_back"
    BROWSER_FORWARD = "browser_forward"
    BROWSER_PAGE_UP = "browser_page_up"
    BROWSER_PAGE_DOWN = "browser_page_down"
    BROWSER_ZOOM_IN = "browser_zoom_in"
    BROWSER_ZOOM_OUT = "browser_zoom_out"
    BROWSER_NEW_TAB = "browser_new_tab"
    # Window intents
    WINDOW_NEXT = "window_next"
    WINDOW_PREV = "window_prev"
    WINDOW_MINIMIZE = "window_minimize"
    WINDOW_MAXIMIZE = "window_maximize"
    WINDOW_RESTORE = "window_restore"
    # Presentation intents
    PRESENTATION_NEXT = "presentation_next"
    PRESENTATION_PREV = "presentation_prev"
    PRESENTATION_START = "presentation_start"
    PRESENTATION_STOP = "presentation_stop"
    # Drawing intents
    DRAW_STROKE = "draw_stroke"
    DRAW_CLEAR = "draw_clear"
    DRAW_UNDO = "draw_undo"
    DRAW_REDO = "draw_redo"
    # Global system intents
    MODE_SWITCH = "mode_switch"
    ACTIVATE_SYSTEM = "activate_system"
    DEACTIVATE_SYSTEM = "deactivate_system"
    EMERGENCY_STOP_TRIGGER = "emergency_stop_trigger"


@dataclass
class Point2D:
    x: float
    y: float

    def distance_to(self, other: Point2D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Point3D:
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: Point3D) -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def as_2d(self) -> Point2D:
        return Point2D(self.x, self.y)

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class HandLandmarks:
    """Represents a set of 21 hand landmarks extracted from a single hand."""
    landmarks: List[Point3D]
    handedness: Handedness = Handedness.UNKNOWN
    score: float = 0.0
    timestamp_ms: float = 0.0
    world_landmarks: Optional[List[Point3D]] = None

    def get(self, index: HandLandmarkIndex | int) -> Point3D:
        idx = int(index)
        return self.landmarks[idx]

    @property
    def wrist(self) -> Point3D:
        return self.landmarks[HandLandmarkIndex.WRIST.value]

    @property
    def index_tip(self) -> Point3D:
        return self.landmarks[HandLandmarkIndex.INDEX_FINGER_TIP.value]

    @property
    def thumb_tip(self) -> Point3D:
        return self.landmarks[HandLandmarkIndex.THUMB_TIP.value]

    @property
    def middle_tip(self) -> Point3D:
        return self.landmarks[HandLandmarkIndex.MIDDLE_FINGER_TIP.value]


@dataclass
class HandFeatures:
    """Calculated normalized geometric and spatial features for a hand."""
    palm_center: Point2D
    hand_scale: float                   # Palm dimension reference for scale-invariance
    finger_extended: Dict[str, bool]    # 'thumb', 'index', 'middle', 'ring', 'pinky'
    finger_curl_angles: Dict[str, float]# Angles in degrees
    thumb_index_dist: float             # Normalized by hand_scale
    thumb_middle_dist: float            # Normalized by hand_scale
    bounding_box: Tuple[float, float, float, float] # (min_x, min_y, max_x, max_y)
    velocity: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    palm_tilt: float = 0.0


@dataclass
class GestureRecognitionResult:
    gesture: GestureType
    confidence: float
    hand_features: Optional[HandFeatures] = None
    handedness: Handedness = Handedness.UNKNOWN
    raw_landmarks: Optional[HandLandmarks] = None
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionIntent:
    intent_type: IntentType
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: float = 0.0
    source_gesture: GestureType = GestureType.NONE
