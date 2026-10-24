"""Temporal State Machine tracking Study Session, Book Closing, Phone Distraction, and Drinking Water."""

from __future__ import annotations
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from app.vision.study_detector import StudyDetectionResult
from app.vision.meme_audio_player import MemeAudioPlayer


class StudyState(str, Enum):
    IDLE = "IDLE"
    READING_BOOK = "READING_BOOK"
    BOOK_CLOSED = "BOOK_CLOSED"
    PHONE_DISTRACTED = "PHONE_DISTRACTED"
    DRINKING_WATER = "DRINKING_WATER"


@dataclass
class StudyEventLog:
    timestamp: float
    state: StudyState
    message: str
    audio_played: Optional[str] = None


class StudyStateMachine:
    """Manages debouncing, transitions, cooldowns, and audio triggers for study activity."""

    def __init__(
        self,
        audio_player: Optional[MemeAudioPlayer] = None,
        min_reading_sec: float = 1.0,
        book_absence_sec: float = 0.8,
        phone_cooldown_sec: float = 8.0,
        drinking_cooldown_sec: float = 8.0,
        book_closed_cooldown_sec: float = 8.0,
        on_state_change: Optional[Callable[[StudyState, str], None]] = None,
    ) -> None:
        self.audio_player = audio_player or MemeAudioPlayer()
        self.min_reading_sec = min_reading_sec
        self.book_absence_sec = book_absence_sec
        self.phone_cooldown_sec = phone_cooldown_sec
        self.drinking_cooldown_sec = drinking_cooldown_sec
        self.book_closed_cooldown_sec = book_closed_cooldown_sec
        self.on_state_change = on_state_change

        self.current_state = StudyState.IDLE
        self.status_message = "Waiting for study activity..."
        self.recent_alert: Optional[str] = None
        self.recent_alert_expiry: float = 0.0

        # Session metrics
        self.total_reading_time: float = 0.0
        self.reading_session_start: Optional[float] = None
        self.distraction_count: int = 0
        self.drinking_count: int = 0
        self.books_completed_count: int = 0

        # Temporal trackers
        self._book_seen_consecutive: int = 0
        self._book_absent_consecutive: int = 0
        self._last_book_seen_time: float = 0.0
        self._was_reading: bool = False
        self._book_closed_and_kept_away: bool = False
        self._book_closed_timestamp: float = 0.0

        self._phone_seen_consecutive: int = 0
        self._last_phone_alert_time: float = 0.0

        self._drinking_consecutive: int = 0
        self._last_drinking_alert_time: float = 0.0
        self._last_book_closed_alert_time: float = 0.0

    def update(self, result: StudyDetectionResult) -> StudyState:
        """Evaluates detection result against temporal rules and triggers memes."""
        now = time.time()

        # 1. Evaluate Drinking Water (Independent High-Priority Hydration Cue)
        if result.is_drinking:
            self._drinking_consecutive += 1
            if self._drinking_consecutive >= 3:
                if (now - self._last_drinking_alert_time) >= self.drinking_cooldown_sec:
                    self._last_drinking_alert_time = now
                    self.drinking_count += 1
                    self._set_alert("💧 Drinking Water Detected! Playing 'Pani Pani!'", 4.0)
                    self.audio_player.play_drinking_water()
                    self._transition(StudyState.DRINKING_WATER, "Hydration Detected: Pani Pani!")
        else:
            self._drinking_consecutive = max(0, self._drinking_consecutive - 1)

        # 2. Evaluate Book Reading & Book Closing
        if result.book_detected:
            self._book_seen_consecutive += 1
            self._book_absent_consecutive = 0
            self._last_book_seen_time = now

            if self._book_seen_consecutive >= 3:
                if not self._was_reading:
                    self._was_reading = True
                    self.reading_session_start = now
                    self._book_closed_and_kept_away = False
                    self._transition(StudyState.READING_BOOK, "📖 Reading Book Detected. Good focus!")
                else:
                    duration = now - (self.reading_session_start or now)
                    self.status_message = f"📖 Reading Book ({int(duration)}s)"
        else:
            self._book_seen_consecutive = 0
            if self._was_reading:
                self._book_absent_consecutive += 1
                time_since_book = now - self._last_book_seen_time

                # Confirm book was closed / set aside
                reading_duration = (self._last_book_seen_time - (self.reading_session_start or self._last_book_seen_time))
                if time_since_book >= self.book_absence_sec:
                    # Book has been closed / kept away!
                    self._was_reading = False
                    self.total_reading_time += max(0.0, reading_duration)
                    self.reading_session_start = None
                    self._book_closed_and_kept_away = True
                    self._book_closed_timestamp = now
                    self.books_completed_count += 1

                    # Trigger "Kyu nahi ho rahi padhai" meme
                    if (now - self._last_book_closed_alert_time) >= self.book_closed_cooldown_sec:
                        self._last_book_closed_alert_time = now
                        self._set_alert("⚠️ Book Closed! Playing 'Kyu Nahi Ho Rahi Padhai?'", 5.0)
                        self.audio_player.play_book_closed()
                        self._transition(StudyState.BOOK_CLOSED, "❌ Book Closed! Kyu nahi ho rahi padhai?")

        # 3. Evaluate Phone Usage After Keeping the Book
        if result.phone_detected:
            self._phone_seen_consecutive += 1
            if self._phone_seen_consecutive >= 3:
                # If the book was closed and kept away OR phone picked up during study session
                if self._book_closed_and_kept_away or self.current_state in (StudyState.BOOK_CLOSED, StudyState.IDLE):
                    if (now - self._last_phone_alert_time) >= self.phone_cooldown_sec:
                        self._last_phone_alert_time = now
                        self.distraction_count += 1
                        self._set_alert("📱 Distraction Detected! Playing 'Abeyy Padhai Likhai Karo!'", 5.0)
                        self.audio_player.play_phone_distraction()
                        self._transition(StudyState.PHONE_DISTRACTED, "🚨 Distraction! Abeyy padhai likhai karo!")
        else:
            self._phone_seen_consecutive = max(0, self._phone_seen_consecutive - 1)

        # Clear expired alert
        if self.recent_alert and now > self.recent_alert_expiry:
            self.recent_alert = None

        return self.current_state

    def _set_alert(self, text: str, duration: float) -> None:
        self.recent_alert = text
        self.recent_alert_expiry = time.time() + duration

    def _transition(self, new_state: StudyState, message: str) -> None:
        self.current_state = new_state
        self.status_message = message
        if self.on_state_change:
            self.on_state_change(new_state, message)

    def trigger_manual_book_read(self) -> None:
        """Simulates book reading."""
        self._was_reading = True
        self.reading_session_start = time.time()
        self._book_closed_and_kept_away = False
        self._transition(StudyState.READING_BOOK, "📖 [Simulated] Reading Book Active")

    def trigger_manual_book_close(self) -> None:
        """Simulates book closing."""
        self._was_reading = False
        self._book_closed_and_kept_away = True
        self._book_closed_timestamp = time.time()
        self._set_alert("⚠️ Book Closed! Playing 'Kyu Nahi Ho Rahi Padhai?'", 5.0)
        self.audio_player.play_book_closed()
        self._transition(StudyState.BOOK_CLOSED, "❌ [Simulated] Book Closed! Kyu nahi ho rahi padhai?")

    def trigger_manual_phone_distraction(self) -> None:
        """Simulates phone distraction."""
        self.distraction_count += 1
        self._set_alert("📱 Phone Detected! Playing 'Abeyy Padhai Likhai Karo!'", 5.0)
        self.audio_player.play_phone_distraction()
        self._transition(StudyState.PHONE_DISTRACTED, "🚨 [Simulated] Phone in use! Abeyy padhai likhai karo!")

    def trigger_manual_drinking(self) -> None:
        """Simulates drinking water."""
        self.drinking_count += 1
        self._set_alert("💧 Drinking Water! Playing 'Pani Pani!'", 4.0)
        self.audio_player.play_drinking_water()
        self._transition(StudyState.DRINKING_WATER, "💧 [Simulated] Hydration: Pani Pani!")

    def reset_session(self) -> None:
        """Resets counters and state."""
        self.current_state = StudyState.IDLE
        self.status_message = "Session reset. Ready for study activity."
        self._was_reading = False
        self._book_closed_and_kept_away = False
        self.reading_session_start = None
        self.recent_alert = "🔄 Session Reset"
        self.recent_alert_expiry = time.time() + 2.0
