"""Unit tests for LandmarkSessionRecorder and LandmarkSessionReplayer."""

import os
import pytest
from app.core.types import (
    HandLandmarks,
    Point3D,
    Handedness,
    GestureType,
)
from app.diagnostics.recorder import LandmarkSessionRecorder, LandmarkSessionReplayer


def test_landmark_record_and_replay(tmp_path):
    session_file = str(tmp_path / "session_test.jsonl")

    recorder = LandmarkSessionRecorder(output_path=session_file)
    recorder.start()

    # Record 5 frames
    for i in range(5):
        pts = [Point3D(0.5 + 0.01 * i, 0.4 + 0.01 * i, 0.0) for _ in range(21)]
        hand = HandLandmarks(landmarks=pts, handedness=Handedness.RIGHT, score=0.98)
        recorder.record_frame([hand], recognized_gesture=GestureType.POINTER, confidence=0.95)

    recorder.stop()
    assert os.path.exists(session_file)

    # Replay
    replayer = LandmarkSessionReplayer(file_path=session_file)
    assert replayer.total_frames == 5

    frames_iterated = 0
    for hands, gest, conf in replayer.iter_frames():
        assert len(hands) == 1
        assert hands[0].handedness == Handedness.RIGHT
        assert len(hands[0].landmarks) == 21
        assert gest == "pointer"
        assert conf == 0.95
        frames_iterated += 1

    assert frames_iterated == 5
