"""Profile Manager persisting and managing distinct user and application configuration profiles."""

from __future__ import annotations
import os
import json
import shutil
from typing import List, Dict, Optional
from app.core.config import (
    GestureOSConfig,
    CursorConfig,
    PinchConfig,
    ActiveRegionConfig,
    GestureValidationConfig,
    CooldownConfig,
)
from app.core.types import InteractionMode
from app.diagnostics.logger import get_logger

logger = get_logger("profile_manager")


class ProfileManager:
    """Manages profile loading, creation, duplication, and disk persistence."""

    def __init__(self, profiles_dir: str = "profiles") -> None:
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)
        self._ensure_built_in_profiles()

    def _ensure_built_in_profiles(self) -> None:
        builtins = {
            "Default": self._create_default_profile(),
            "Media": self._create_media_profile(),
            "Gaming": self._create_gaming_profile(),
            "Presentation": self._create_presentation_profile(),
            "Accessibility": self._create_accessibility_profile(),
        }

        for name, cfg in builtins.items():
            filepath = os.path.join(self.profiles_dir, f"{name.lower()}.json")
            if not os.path.isfile(filepath):
                cfg.save_to_file(filepath)

    def _create_default_profile(self) -> GestureOSConfig:
        return GestureOSConfig(profile_name="Default", default_mode=InteractionMode.MOUSE)

    def _create_media_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(
            profile_name="Media",
            default_mode=InteractionMode.MEDIA,
        )
        cfg.cursor.smoothing_level = "high"
        return cfg

    def _create_gaming_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(
            profile_name="Gaming",
            default_mode=InteractionMode.MOUSE,
        )
        cfg.cursor.smoothing_filter = "one_euro"
        cfg.cursor.smoothing_level = "low"
        cfg.cursor.velocity_limit = 140.0
        cfg.pinch.cooldown_ms = 140
        return cfg

    def _create_presentation_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(
            profile_name="Presentation",
            default_mode=InteractionMode.PRESENTATION,
        )
        cfg.cursor.smoothing_level = "high"
        cfg.validation.swipe_min_distance = 0.15
        return cfg

    def _create_accessibility_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(
            profile_name="Accessibility",
            default_mode=InteractionMode.MOUSE,
        )
        # Slower, more forgiving timing, stronger smoothing
        cfg.cursor.smoothing_level = "high"
        cfg.active_region.dead_zone_radius = 0.006
        cfg.pinch.pinch_threshold = 0.35  # Easier to pinch
        cfg.pinch.release_threshold = 0.44
        cfg.validation.consecutive_frames_required = 4
        cfg.cooldowns.left_click_ms = 350
        return cfg

    def list_profiles(self) -> List[str]:
        profiles = []
        for f in os.listdir(self.profiles_dir):
            if f.endswith(".json"):
                profiles.append(os.path.splitext(f)[0].capitalize())
        return sorted(profiles)

    def load_profile(self, name: str) -> GestureOSConfig:
        filename = f"{name.lower()}.json"
        path = os.path.join(self.profiles_dir, filename)
        if os.path.isfile(path):
            logger.info(f"Loaded profile: {name}")
            return GestureOSConfig.load_from_file(path)
        logger.warning(f"Profile '{name}' not found, returning Default profile.")
        return self._create_default_profile()

    def save_profile(self, config: GestureOSConfig) -> str:
        filename = f"{config.profile_name.lower()}.json"
        path = os.path.join(self.profiles_dir, filename)
        config.save_to_file(path)
        logger.info(f"Saved profile '{config.profile_name}' to {path}")
        return path

    def duplicate_profile(self, source_name: str, new_name: str) -> bool:
        src_path = os.path.join(self.profiles_dir, f"{source_name.lower()}.json")
        dst_path = os.path.join(self.profiles_dir, f"{new_name.lower()}.json")
        if not os.path.isfile(src_path) or os.path.isfile(dst_path):
            return False
        shutil.copyfile(src_path, dst_path)
        logger.info(f"Duplicated profile {source_name} -> {new_name}")
        return True

    def delete_profile(self, name: str) -> bool:
        if name.lower() in ("default", "media", "gaming", "presentation", "accessibility"):
            # Protected built-in profiles
            return False
        path = os.path.join(self.profiles_dir, f"{name.lower()}.json")
        if os.path.isfile(path):
            os.remove(path)
            logger.info(f"Deleted profile: {name}")
            return True
        return False
