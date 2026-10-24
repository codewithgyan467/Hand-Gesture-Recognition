"""Unified, portable Resource Manager for GestureOS and StudyGuard.

Discovers, validates, and manages paths for models, audio assets, configuration,
profiles, and logs across Portable Mode, Installed Mode, and PyInstaller frozen bundles.
Never uses hardcoded drive letters or developer-specific paths.
"""

from __future__ import annotations
import os
import sys
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceStatus:
    name: str
    path: Path
    exists: bool
    size_bytes: int
    is_valid: bool
    error_message: Optional[str] = None


class ResourceManager:
    """Universal path discovery and resource manager using pathlib.Path."""

    APP_NAME = "GestureOS"
    ORGANIZATION_NAME = "GestureOS"

    def __init__(self, override_base_dir: Optional[Path] = None, force_portable: bool = False) -> None:
        self._override_base_dir = override_base_dir
        self._force_portable = force_portable

        # 1. Determine Application Root Directory
        self.app_dir = self._detect_app_dir()

        # 2. Determine Data & Config Directories (Portable vs Installed)
        self.is_portable = self._detect_is_portable()
        self.user_data_dir = self._detect_user_data_dir()
        self.config_dir = self.user_data_dir / "config"
        self.profiles_dir = self.user_data_dir / "profiles"
        self.logs_dir = self.user_data_dir / "logs"
        self.cache_dir = self.user_data_dir / "cache"

        # 3. Determine Asset & Model Directories
        self.models_dir = self._detect_models_dir()
        self.audio_dir = self._detect_audio_dir()

        # 4. Ensure runtime writable directories exist
        for d in [self.config_dir, self.profiles_dir, self.logs_dir, self.cache_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _detect_app_dir(self) -> Path:
        """Locates the core installation or code directory."""
        if self._override_base_dir:
            return self._override_base_dir.resolve()

        # PyInstaller bundle extraction directory
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS).resolve()

        # Normal Python execution: navigate up from this file (app/core/resources.py -> GestureOS)
        return Path(__file__).resolve().parent.parent.parent

    def _detect_is_portable(self) -> bool:
        """Checks if portable marker exists or if running from local repo/portable folder."""
        if self._force_portable:
            return True

        # Check for explicit portable marker file
        if (self.app_dir / "PORTABLE").exists() or (self.app_dir.parent / "PORTABLE").exists():
            return True

        # If running from source repository (parent directory contains .git or meme audios)
        repo_root = self.app_dir.parent
        if (repo_root / ".git").exists() or (self.app_dir / ".git").exists():
            return True

        # Check if local profiles directory exists alongside app
        if (self.app_dir / "profiles").is_dir():
            return True

        return False

    def _detect_user_data_dir(self) -> Path:
        """Returns portable local directory or OS-standard AppData/Config directory."""
        if self.is_portable:
            return self.app_dir

        # Standard OS directories
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            if base:
                return Path(base) / self.ORGANIZATION_NAME / self.APP_NAME
            return Path.home() / f".{self.APP_NAME.lower()}"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / self.APP_NAME
        else:  # Linux / FreeDesktop
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                return Path(xdg_config) / self.APP_NAME.lower()
            return Path.home() / ".config" / self.APP_NAME.lower()

    def _detect_models_dir(self) -> Path:
        """Finds directory containing MediaPipe and TFLite neural models."""
        candidates = [
            self.app_dir / "models",
            self.app_dir.parent / "models",
            self.app_dir / "GestureOS" / "models",
            Path.cwd() / "models",
            Path.cwd() / "GestureOS" / "models",
        ]
        for c in candidates:
            if c.is_dir() and (c / "hand_landmarker.task").exists():
                return c.resolve()
        # Fallback to standard app_dir/models
        return (self.app_dir / "models").resolve()

    def _detect_audio_dir(self) -> Path:
        """Finds directory containing StudyGuard meme sound files."""
        candidates = [
            self.app_dir / "meme audios",
            self.app_dir.parent / "meme audios",
            self.app_dir / "audio",
            Path.cwd() / "meme audios",
            Path.cwd() / "GestureOS" / "meme audios",
        ]
        for c in candidates:
            if c.is_dir() and any(c.glob("*.mp3")):
                return c.resolve()
        # Fallback to app_dir/meme audios
        return (self.app_dir / "meme audios").resolve()

    # ------------------------------------------------------------------
    # Model Accessors & Validation
    # ------------------------------------------------------------------

    def get_hand_model_path(self) -> Path:
        return self.models_dir / "hand_landmarker.task"

    def get_object_model_path(self) -> Path:
        return self.models_dir / "efficientdet_lite0.tflite"

    def get_face_model_path(self) -> Path:
        return self.models_dir / "blaze_face_short_range.tflite"

    def validate_model(self, model_name: str, min_expected_bytes: int = 1000) -> ResourceStatus:
        """Verifies file existence and minimum size integrity."""
        path = self.models_dir / model_name
        if not path.is_file():
            return ResourceStatus(
                name=model_name,
                path=path,
                exists=False,
                size_bytes=0,
                is_valid=False,
                error_message=f"Model file '{model_name}' missing from: {path}",
            )
        sz = path.stat().st_size
        if sz < min_expected_bytes:
            return ResourceStatus(
                name=model_name,
                path=path,
                exists=True,
                size_bytes=sz,
                is_valid=False,
                error_message=f"Model file '{model_name}' appears corrupt or incomplete ({sz} bytes).",
            )
        return ResourceStatus(
            name=model_name,
            path=path,
            exists=True,
            size_bytes=sz,
            is_valid=True,
        )

    def validate_all_models(self) -> Dict[str, ResourceStatus]:
        return {
            "hand_landmarker.task": self.validate_model("hand_landmarker.task", min_expected_bytes=5_000_000),
            "efficientdet_lite0.tflite": self.validate_model("efficientdet_lite0.tflite", min_expected_bytes=10_000_000),
            "blaze_face_short_range.tflite": self.validate_model("blaze_face_short_range.tflite", min_expected_bytes=150_000),
        }

    # ------------------------------------------------------------------
    # Audio Accessors & Validation
    # ------------------------------------------------------------------

    def get_audio_path(self, filename: str) -> Path:
        return self.audio_dir / filename

    def get_study_audio_paths(self) -> Dict[str, Path]:
        return {
            "book_closed": self.get_audio_path("kyu-nahi-ho-rahi-padhai.mp3"),
            "phone_distracted": self.get_audio_path("abeyy-padhai-likhai-karo.mp3"),
            "drinking_water": self.get_audio_path("pani pani.mp3"),
        }

    def validate_audio_files(self) -> Dict[str, ResourceStatus]:
        results = {}
        for key, path in self.get_study_audio_paths().items():
            fname = path.name
            if not path.is_file():
                results[key] = ResourceStatus(
                    name=fname,
                    path=path,
                    exists=False,
                    size_bytes=0,
                    is_valid=False,
                    error_message=f"Audio asset '{fname}' unavailable at: {path}",
                )
            else:
                sz = path.stat().st_size
                results[key] = ResourceStatus(
                    name=fname,
                    path=path,
                    exists=True,
                    size_bytes=sz,
                    is_valid=sz > 5000,
                    error_message=None if sz > 5000 else "Audio file appears truncated",
                )
        return results

    # ------------------------------------------------------------------
    # Profiles & Configuration File Paths
    # ------------------------------------------------------------------

    def get_profile_path(self, profile_name: str) -> Path:
        clean_name = profile_name.lower().replace(" ", "_")
        return self.profiles_dir / f"{clean_name}.json"

    def get_default_config_path(self) -> Path:
        return self.config_dir / "gestureos_config.json"

    def get_log_file_path(self) -> Path:
        return self.logs_dir / "gestureos.log"

    # Class-level accessors
    @classmethod
    def get_instance(cls) -> ResourceManager:
        return get_resource_manager()

    @classmethod
    def get_logs_dir(cls) -> Path:
        return get_resource_manager().logs_dir

    @classmethod
    def get_config_dir(cls) -> Path:
        return get_resource_manager().config_dir

    @classmethod
    def get_models_dir(cls) -> Path:
        return get_resource_manager().models_dir

    @classmethod
    def get_audio_dir(cls) -> Path:
        return get_resource_manager().audio_dir

    @classmethod
    def validate_models(cls) -> Dict[str, bool]:
        inst = get_resource_manager()
        return {k: v.is_valid for k, v in inst.validate_all_models().items()}

    @classmethod
    def validate_audio_assets(cls) -> Dict[str, bool]:
        inst = get_resource_manager()
        return {k: v.is_valid for k, v in inst.validate_audio_files().items()}


# Global lazy-initialized resource manager instance
_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Returns the process-wide ResourceManager singleton."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager
