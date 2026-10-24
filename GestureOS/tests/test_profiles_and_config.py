"""Unit tests for configuration loading, serialization, and profile management."""

import os
import pytest
from app.core.config import GestureOSConfig
from app.calibration.profile_manager import ProfileManager
from app.core.types import InteractionMode


def test_config_serialization_roundtrip(tmp_path):
    cfg = GestureOSConfig(profile_name="TestProfile", default_mode=InteractionMode.MEDIA)
    cfg.cursor.smoothing_level = "high"
    cfg.pinch.cooldown_ms = 330

    file_path = str(tmp_path / "test_cfg.json")
    cfg.save_to_file(file_path)

    loaded = GestureOSConfig.load_from_file(file_path)
    assert loaded.profile_name == "TestProfile"
    assert loaded.default_mode == InteractionMode.MEDIA
    assert loaded.cursor.smoothing_level == "high"
    assert loaded.pinch.cooldown_ms == 330


def test_profile_manager_builtins(tmp_path):
    prof_dir = str(tmp_path / "profiles")
    mgr = ProfileManager(profiles_dir=prof_dir)

    profiles = mgr.list_profiles()
    assert "Default" in profiles
    assert "Media" in profiles
    assert "Gaming" in profiles
    assert "Accessibility" in profiles

    media_cfg = mgr.load_profile("Media")
    assert media_cfg.default_mode == InteractionMode.MEDIA

    gaming_cfg = mgr.load_profile("Gaming")
    assert gaming_cfg.cursor.smoothing_level == "low"
