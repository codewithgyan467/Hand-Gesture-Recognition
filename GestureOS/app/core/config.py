"""Centralized, versioned configuration management for GestureOS."""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from app.core.types import InteractionMode, GestureType, IntentType


@dataclass
class CameraConfig:
    camera_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    auto_reconnect: bool = True
    reconnect_interval_sec: float = 2.0
    mirror: bool = True
    simulation_mode: bool = False


@dataclass
class ActiveRegionConfig:
    """Active control zone normalized to [0, 1] frame dimensions."""
    x_min: float = 0.15
    y_min: float = 0.15
    x_max: float = 0.85
    y_max: float = 0.85
    dead_zone_radius: float = 0.003  # Ignore jitter below this normalized delta


@dataclass
class CursorConfig:
    smoothing_filter: str = "one_euro"  # "one_euro", "ema", "kalman", "none"
    smoothing_level: str = "medium"     # "low", "medium", "high"
    min_cutoff: float = 1.0             # One Euro filter min_cutoff
    beta: float = 0.007                 # One Euro filter speed coefficient
    d_cutoff: float = 1.0               # One Euro derivative cutoff
    ema_alpha: float = 0.35             # Exponential moving average alpha
    acceleration: float = 1.15          # Non-linear pointer acceleration
    velocity_limit: float = 85.0        # Max jump pixels per frame to prevent teleports
    screen_width: int = 1920
    screen_height: int = 1080
    invert_x: bool = True               # Inverts horizontal axis so cursor moves naturally with hand


@dataclass
class PinchConfig:
    pinch_threshold: float = 0.28       # Distance ratio normalized by palm scale to trigger pinch
    release_threshold: float = 0.36     # Hysteresis release threshold
    pinch_hold_time_sec: float = 0.35   # Duration required to initiate drag or hold
    double_click_window_sec: float = 0.40 # Max interval between clicks for double-click
    cooldown_ms: int = 250              # Minimum delay between distinct pinch clicks
    movement_drag_threshold: float = 0.035 # Movement delta required to immediately initiate drag


@dataclass
class GestureValidationConfig:
    min_confidence: float = 0.70
    consecutive_frames_required: int = 3
    activation_hold_sec: float = 1.0    # Open palm hold duration for system activation
    allow_gesture_activation: bool = False # False = Passive mode strictly controlled by user button/hotkey
    emergency_stop_gesture: str = "dual_fists" # Dual fists or ESC key
    rate_limit_volume_hz: float = 15.0  # Max volume updates per second
    swipe_min_velocity: float = 0.45    # Normalized distance per second
    swipe_min_distance: float = 0.12    # Normalized distance in frame
    wave_oscillations_required: int = 3


@dataclass
class CooldownConfig:
    left_click_ms: int = 220
    right_click_ms: int = 350
    double_click_ms: int = 400
    scroll_ms: int = 30
    swipe_ms: int = 500
    mode_switch_ms: int = 800
    system_command_ms: int = 600


@dataclass
class GestureOSConfig:
    version: str = "1.0.0"
    profile_name: str = "Default"
    default_mode: InteractionMode = InteractionMode.MOUSE
    camera: CameraConfig = field(default_factory=CameraConfig)
    active_region: ActiveRegionConfig = field(default_factory=ActiveRegionConfig)
    cursor: CursorConfig = field(default_factory=CursorConfig)
    pinch: PinchConfig = field(default_factory=PinchConfig)
    validation: GestureValidationConfig = field(default_factory=GestureValidationConfig)
    cooldowns: CooldownConfig = field(default_factory=CooldownConfig)
    
    # Custom mappings: Mode -> Gesture -> Intent
    custom_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Mode preferences
    simple_mode: bool = True

    # UI preferences
    show_debug_overlay: bool = True
    show_hud: bool = True
    start_minimized_to_tray: bool = False
    launch_on_startup: bool = False
    dark_mode: bool = True
    enable_study_guard: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert enums to string values
        data["default_mode"] = self.default_mode.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GestureOSConfig:
        cfg = cls()
        if "version" in data:
            cfg.version = data["version"]
        if "profile_name" in data:
            cfg.profile_name = data["profile_name"]
        if "default_mode" in data:
            try:
                cfg.default_mode = InteractionMode(data["default_mode"])
            except ValueError:
                cfg.default_mode = InteractionMode.MOUSE

        if "camera" in data and isinstance(data["camera"], dict):
            cfg.camera = CameraConfig(**{k: v for k, v in data["camera"].items() if hasattr(CameraConfig, k)})
        if "active_region" in data and isinstance(data["active_region"], dict):
            cfg.active_region = ActiveRegionConfig(**{k: v for k, v in data["active_region"].items() if hasattr(ActiveRegionConfig, k)})
        if "cursor" in data and isinstance(data["cursor"], dict):
            cfg.cursor = CursorConfig(**{k: v for k, v in data["cursor"].items() if hasattr(CursorConfig, k)})
        if "pinch" in data and isinstance(data["pinch"], dict):
            cfg.pinch = PinchConfig(**{k: v for k, v in data["pinch"].items() if hasattr(PinchConfig, k)})
        if "validation" in data and isinstance(data["validation"], dict):
            cfg.validation = GestureValidationConfig(**{k: v for k, v in data["validation"].items() if hasattr(GestureValidationConfig, k)})
        if "cooldowns" in data and isinstance(data["cooldowns"], dict):
            cfg.cooldowns = CooldownConfig(**{k: v for k, v in data["cooldowns"].items() if hasattr(CooldownConfig, k)})
        if "custom_mappings" in data and isinstance(data["custom_mappings"], dict):
            cfg.custom_mappings = data["custom_mappings"]

        for bool_field in ["simple_mode", "show_debug_overlay", "show_hud", "start_minimized_to_tray", "launch_on_startup", "dark_mode", "enable_study_guard"]:
            if bool_field in data:
                setattr(cfg, bool_field, bool(data[bool_field]))

        return cfg

    def save_to_file(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> GestureOSConfig:
        if not os.path.isfile(filepath):
            return cls()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return cls()
