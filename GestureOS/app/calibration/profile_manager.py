"""Profile Manager persisting and managing distinct user and application configuration profiles."""

from __future__ import annotations
import os
import json
import shutil
from pathlib import Path
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
from app.core.resources import get_resource_manager
from app.diagnostics.logger import get_logger

logger = get_logger("profile_manager")


class ProfileManager:
    """Manages profile loading, creation, duplication, import, export, and disk persistence."""

    PROTECTED_PROFILES = {"default", "media", "gaming", "presentation", "accessibility", "browser", "study"}

    def __init__(self, profiles_dir: Optional[str | Path] = None) -> None:
        if profiles_dir is None:
            self.profiles_dir = str(get_resource_manager().profiles_dir)
        else:
            self.profiles_dir = str(Path(profiles_dir).resolve())

        os.makedirs(self.profiles_dir, exist_ok=True)
        self._ensure_built_in_profiles()

    def _ensure_built_in_profiles(self) -> None:
        builtins = {
            "Default": self._create_default_profile(),
            "Media": self._create_media_profile(),
            "Gaming": self._create_gaming_profile(),
            "Presentation": self._create_presentation_profile(),
            "Browser": self._create_browser_profile(),
            "Accessibility": self._create_accessibility_profile(),
            "Study": self._create_study_profile(),
            "Custom": self._create_custom_profile(),
        }

        for name, cfg in builtins.items():
            filepath = os.path.join(self.profiles_dir, f"{name.lower()}.json")
            if not os.path.isfile(filepath):
                cfg.save_to_file(filepath)

    def _create_default_profile(self) -> GestureOSConfig:
        return GestureOSConfig(profile_name="Default", default_mode=InteractionMode.MOUSE)

    def _create_media_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Media", default_mode=InteractionMode.MEDIA)
        cfg.cursor.smoothing_level = "high"
        return cfg

    def _create_gaming_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Gaming", default_mode=InteractionMode.MOUSE)
        cfg.cursor.smoothing_filter = "one_euro"
        cfg.cursor.smoothing_level = "low"
        cfg.cursor.velocity_limit = 140.0
        cfg.pinch.cooldown_ms = 140
        return cfg

    def _create_presentation_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Presentation", default_mode=InteractionMode.PRESENTATION)
        cfg.cursor.smoothing_level = "high"
        cfg.validation.swipe_min_distance = 0.15
        return cfg

    def _create_browser_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Browser", default_mode=InteractionMode.BROWSER)
        cfg.cursor.smoothing_level = "medium"
        return cfg

    def _create_accessibility_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Accessibility", default_mode=InteractionMode.MOUSE)
        cfg.cursor.smoothing_level = "high"
        cfg.active_region.dead_zone_radius = 0.006
        cfg.pinch.pinch_threshold = 0.35  # Easier to pinch
        cfg.pinch.release_threshold = 0.44
        cfg.validation.consecutive_frames_required = 4
        cfg.cooldowns.left_click_ms = 350
        return cfg

    def _create_study_profile(self) -> GestureOSConfig:
        cfg = GestureOSConfig(profile_name="Study", default_mode=InteractionMode.MOUSE)
        cfg.enable_study_guard = True
        return cfg

    def _create_custom_profile(self) -> GestureOSConfig:
        return GestureOSConfig(profile_name="Custom", default_mode=InteractionMode.MOUSE)

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
        if name.lower() in self.PROTECTED_PROFILES:
            return False
        path = os.path.join(self.profiles_dir, f"{name.lower()}.json")
        if os.path.isfile(path):
            os.remove(path)
            logger.info(f"Deleted profile: {name}")
            return True
        return False

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        if old_name.lower() in self.PROTECTED_PROFILES:
            return False
        old_path = os.path.join(self.profiles_dir, f"{old_name.lower()}.json")
        new_path = os.path.join(self.profiles_dir, f"{new_name.lower()}.json")
        if not os.path.isfile(old_path) or os.path.isfile(new_path):
            return False
        os.rename(old_path, new_path)
        # Update internal profile_name in JSON
        cfg = GestureOSConfig.load_from_file(new_path)
        cfg.profile_name = new_name
        cfg.save_to_file(new_path)
        return True

    def export_profile(self, name: str, export_path: str | Path) -> bool:
        cfg = self.load_profile(name)
        cfg.save_to_file(str(export_path))
        return True

    def import_profile(self, import_path: str | Path) -> Optional[str]:
        path_str = str(import_path)
        if not os.path.isfile(path_str):
            return None
        try:
            cfg = GestureOSConfig.load_from_file(path_str)
            target_name = cfg.profile_name or Path(import_path).stem.capitalize()
            cfg.profile_name = target_name
            self.save_profile(cfg)
            return target_name
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return None

    def reset_profile(self, name: str) -> bool:
        """Resets a built-in profile back to factory default parameters."""
        creators = {
            "default": self._create_default_profile,
            "media": self._create_media_profile,
            "gaming": self._create_gaming_profile,
            "presentation": self._create_presentation_profile,
            "browser": self._create_browser_profile,
            "accessibility": self._create_accessibility_profile,
            "study": self._create_study_profile,
            "custom": self._create_custom_profile,
        }
        creator = creators.get(name.lower())
        if creator:
            cfg = creator()
            self.save_profile(cfg)
            return True
        return False
