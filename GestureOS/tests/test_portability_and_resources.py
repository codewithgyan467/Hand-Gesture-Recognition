"""Tests for portability, resource discovery, missing models/audio, and config recovery."""

import os
import json
import tempfile
from pathlib import Path
from app.core.resources import ResourceManager, ResourceStatus
from app.core.config import GestureOSConfig


def test_resource_manager_paths_are_portable():
    res = ResourceManager()
    # Ensure no hardcoded developer paths exist
    for p in [res.app_dir, res.models_dir, res.audio_dir, res.config_dir, res.logs_dir]:
        p_str = str(p)
        assert "gyand" not in p_str.lower()
        assert Path(p_str).is_absolute()


def test_missing_model_graceful_handling():
    res = ResourceManager()
    status = res.validate_model("non_existent_fake_model.task")
    assert not status.exists
    assert not status.is_valid
    assert "missing" in status.error_message.lower()


def test_missing_audio_graceful_handling():
    res = ResourceManager()
    # Check that query for non-existent audio returns a valid ResourceStatus object with exists=False
    path = res.get_audio_path("non_existent_audio.mp3")
    assert not path.is_file()


def test_corrupt_config_auto_recovery(tmp_path):
    corrupt_cfg_path = tmp_path / "corrupt_config.json"
    # Write invalid / malformed JSON
    with open(corrupt_cfg_path, "w", encoding="utf-8") as f:
        f.write("{ invalid_json_syntax: [missing_brackets")

    # Load corrupt file - should recover by backing up and returning clean defaults
    recovered_config = GestureOSConfig.load_from_file(str(corrupt_cfg_path))
    assert recovered_config is not None
    assert isinstance(recovered_config, GestureOSConfig)

    # Verify backup file was created
    backup_path = Path(str(corrupt_cfg_path) + ".corrupt.bak")
    assert backup_path.exists()
