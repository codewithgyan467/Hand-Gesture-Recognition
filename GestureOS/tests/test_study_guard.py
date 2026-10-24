"""Unit and Integration Tests for StudyGuard Meme Distraction & Hydration Monitor."""

from __future__ import annotations
import os
import time
import numpy as np
import pytest

from app.vision.meme_audio_player import MemeAudioPlayer
from app.vision.study_detector import StudyVisionDetector, StudyDetectionResult
from app.vision.study_state_machine import StudyStateMachine, StudyState


class MockAudioPlayer(MemeAudioPlayer):
    """Mock audio player for automated test runs without hardware audio output."""

    def __init__(self) -> None:
        super().__init__(muted=True)
        self.played_events: list[str] = []

    def play_book_closed(self, block: bool = False) -> bool:
        self.played_events.append("book_closed")
        return True

    def play_phone_distraction(self, block: bool = False) -> bool:
        self.played_events.append("phone_distraction")
        return True

    def play_drinking_water(self, block: bool = False) -> bool:
        self.played_events.append("drinking_water")
        return True


def test_audio_player_resolution():
    player = MemeAudioPlayer()
    assert os.path.exists(player.kyu_nahi_path), f"File missing: {player.kyu_nahi_path}"
    assert os.path.exists(player.abeyy_path), f"File missing: {player.abeyy_path}"
    assert os.path.exists(player.pani_pani_path), f"File missing: {player.pani_pani_path}"


def test_audio_player_mute_toggle():
    player = MemeAudioPlayer(muted=False)
    assert not player.muted
    player.toggle_mute()
    assert player.muted
    player.toggle_mute()
    assert not player.muted


def test_vision_detector_initialization():
    detector = StudyVisionDetector()
    assert detector._obj_detector is not None, "Object detector failed to initialize"
    assert detector._face_detector is not None, "Face detector failed to initialize"

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = detector.detect(blank_frame)
    assert isinstance(res, StudyDetectionResult)
    assert not res.book_detected
    assert not res.phone_detected
    assert not res.is_drinking


def test_state_machine_book_reading_to_close():
    mock_audio = MockAudioPlayer()
    sm = StudyStateMachine(
        audio_player=mock_audio,
        book_absence_sec=0.1,  # Fast for unit tests
        book_closed_cooldown_sec=0.5,
    )

    # 1. Initially IDLE
    assert sm.current_state == StudyState.IDLE

    # 2. Feed book detected frames
    book_res = StudyDetectionResult(book_detected=True, book_score=0.85, book_box=(100, 100, 300, 300))
    for _ in range(4):
        sm.update(book_res)

    assert sm.current_state == StudyState.READING_BOOK
    assert sm._was_reading is True

    # 3. Book is closed / kept away (no book in frame)
    time.sleep(0.12)
    no_book_res = StudyDetectionResult(book_detected=False)
    for _ in range(3):
        sm.update(no_book_res)

    # State must transition to BOOK_CLOSED and play "Kyu nahi ho rahi padhai"
    assert sm.current_state == StudyState.BOOK_CLOSED
    assert "book_closed" in mock_audio.played_events
    assert sm.books_completed_count >= 1


def test_state_machine_phone_distraction_after_book():
    mock_audio = MockAudioPlayer()
    sm = StudyStateMachine(
        audio_player=mock_audio,
        book_absence_sec=0.05,
        phone_cooldown_sec=1.0,
    )

    # Step 1: Read book
    book_res = StudyDetectionResult(book_detected=True, book_score=0.9)
    for _ in range(4):
        sm.update(book_res)

    # Step 2: Close book
    time.sleep(0.08)
    no_book_res = StudyDetectionResult(book_detected=False)
    for _ in range(3):
        sm.update(no_book_res)

    assert sm.current_state == StudyState.BOOK_CLOSED
    assert "book_closed" in mock_audio.played_events

    # Step 3: Pick up phone
    phone_res = StudyDetectionResult(phone_detected=True, phone_score=0.92, phone_box=(200, 200, 280, 400))
    for _ in range(4):
        sm.update(phone_res)

    # Must transition to PHONE_DISTRACTED and play "Abeyy padhai likhai karo"
    assert sm.current_state == StudyState.PHONE_DISTRACTED
    assert "phone_distraction" in mock_audio.played_events
    assert sm.distraction_count >= 1


def test_state_machine_drinking_water():
    mock_audio = MockAudioPlayer()
    sm = StudyStateMachine(
        audio_player=mock_audio,
        drinking_cooldown_sec=1.0,
    )

    # Feed drinking water frames
    drink_res = StudyDetectionResult(
        container_detected=True,
        container_label="bottle",
        is_drinking=True,
        drinking_confidence=0.88,
    )
    for _ in range(4):
        sm.update(drink_res)

    assert sm.current_state == StudyState.DRINKING_WATER
    assert "drinking_water" in mock_audio.played_events
    assert sm.drinking_count >= 1


def test_state_machine_cooldown():
    mock_audio = MockAudioPlayer()
    sm = StudyStateMachine(
        audio_player=mock_audio,
        phone_cooldown_sec=2.0,
    )

    phone_res = StudyDetectionResult(phone_detected=True, phone_score=0.9)
    # Trigger 1st time
    for _ in range(4):
        sm.update(phone_res)

    initial_count = mock_audio.played_events.count("phone_distraction")
    assert initial_count == 1

    # Keep holding phone for 10 more frames (within cooldown window)
    for _ in range(10):
        sm.update(phone_res)

    # Audio should NOT have been re-triggered due to cooldown
    assert mock_audio.played_events.count("phone_distraction") == 1
