"""Centralized, versioned configuration management for GestureOS and StudyGuard."""

from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from app.core.types import InteractionMode, GestureType, IntentType
from app.diagnostics.logger import get_logger

logger = get_logger("config")


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
class StudyGuardConfig:
    """Configurable behavioral rules and audio options for StudyGuard."""
    enabled: bool = False
    book_absence_sec: float = 0.8
    phone_detection_window_sec: float = 15.0
    drinking_proximity_threshold: float = 0.22
    min_object_confidence: float = 0.28
    min_face_confidence: float = 0.40
    cooldown_sec: float = 7.0
    audio_volume: float = 1.0
    quiet_mode: bool = False
    mute_mode: bool = False
    smart_cooldown: bool = True
    detection_fps: int = 10


@dataclass
class AccessibilityConfig:
    """Specialized assistive settings for motor and vision accessibility."""
    large_ui: bool = False
    high_contrast: bool = False
    reduced_motion: bool = False
    slow_cursor: bool = False
    dwell_click: bool = False
    dwell_time_sec: float = 1.2
    dwell_radius: float = 0.02


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
    study_guard: StudyGuardConfig = field(default_factory=StudyGuardConfig)
    accessibility: AccessibilityConfig = field(default_factory=AccessibilityConfig)
    
    # Custom mappings: Mode -> Gesture -> Intent
    custom_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Application-specific profile switching
    auto_switch_foreground_profiles: bool = False
    app_profile_mappings: Dict[str, str] = field(default_factory=lambda: {
        "chrome.exe": "Browser",
        "powerpnt.exe": "Presentation",
        "vlc.exe": "Media",
        "code.exe": "Default",
    })

    # Mode preferences
    simple_mode: bool = True

    # Performance tier: "auto", "full", "balanced", "light", "compatibility"
    performance_tier: str = "auto"

    # UI preferences
    show_debug_overlay: bool = True
    show_hud: bool = True
    start_minimized_to_tray: bool = False
    launch_on_startup: bool = False
    dark_mode: bool = True

    # Deprecated top-level mirror for backwards compatibility
    @property
    def enable_study_guard(self) -> bool:
        return self.study_guard.enabled

    @enable_study_guard.setter
    def enable_study_guard(self, val: bool) -> None:
        self.study_guard.enabled = val

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["default_mode"] = self.default_mode.value
        data["enable_study_guard"] = self.study_guard.enabled
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GestureOSConfig:
        cfg = cls()
        if "version" in data:
            cfg.version = str(data["version"])
        if "profile_name" in data:
            cfg.profile_name = str(data["profile_name"])
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
        if "study_guard" in data and isinstance(data["study_guard"], dict):
            cfg.study_guard = StudyGuardConfig(**{k: v for k, v in data["study_guard"].items() if hasattr(StudyGuardConfig, k)})
        elif "enable_study_guard" in data:
            cfg.study_guard.enabled = bool(data["enable_study_guard"])

        if "accessibility" in data and isinstance(data["accessibility"], dict):
            cfg.accessibility = AccessibilityConfig(**{k: v for k, v in data["accessibility"].items() if hasattr(AccessibilityConfig, k)})

        if "custom_mappings" in data and isinstance(data["custom_mappings"], dict):
            cfg.custom_mappings = data["custom_mappings"]
        if "app_profile_mappings" in data and isinstance(data["app_profile_mappings"], dict):
            cfg.app_profile_mappings = data["app_profile_mappings"]

        if "performance_tier" in data:
            cfg.performance_tier = str(data["performance_tier"])

        for bool_field in [
            "simple_mode", "show_debug_overlay", "show_hud", "start_minimized_to_tray",
            "launch_on_startup", "dark_mode", "auto_switch_foreground_profiles"
        ]:
            if bool_field in data:
                setattr(cfg, bool_field, bool(data[bool_field]))

        return cfg

    def save_to_file(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> GestureOSConfig:
        """Loads configuration from JSON file with automatic corrupt configuration recovery."""
        if not os.path.isfile(filepath):
            return cls()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.critical(f"Configuration file '{filepath}' is corrupted: {e}. Initiating safe recovery...")
            # 1. Back up corrupt config
            backup_path = f"{filepath}.corrupt.bak"
            try:
                shutil.copyfile(filepath, backup_path)
                logger.warning(f"Backed up corrupted configuration to: {backup_path}")
            except Exception as be:
                logger.error(f"Failed to create config backup: {be}")

            # 2. Instantiate clean defaults
            recovered = cls()

            # 3. Write clean configuration to restore usability
            try:
                recovered.save_to_file(filepath)
                logger.info(f"Re-initialized clean default configuration at: {filepath}")
            except Exception as we:
                logger.error(f"Could not overwrite corrupted config file: {we}")

            return recovered
