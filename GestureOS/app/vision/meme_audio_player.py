"""Meme Audio Player for StudyGuard using portable ResourceManager and AudioProvider."""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from app.core.resources import get_resource_manager
from app.platform.audio import BaseAudioProvider, get_audio_provider


class MemeAudioPlayer:
    """Plays meme audio files asynchronously without stalling the computer vision loop."""

    def __init__(
        self,
        kyu_nahi_path: Optional[str | Path] = None,
        abeyy_path: Optional[str | Path] = None,
        pani_pani_path: Optional[str | Path] = None,
        muted: bool = False,
        audio_provider: Optional[BaseAudioProvider] = None,
    ) -> None:
        self.rm = get_resource_manager()
        self.provider = audio_provider or get_audio_provider()
        self.provider.muted = muted

        # Dynamically discover audio paths without hardcoded drive letters
        audio_paths = self.rm.get_study_audio_paths()
        self.kyu_nahi_path = str(Path(kyu_nahi_path).resolve()) if kyu_nahi_path else str(audio_paths["book_closed"])
        self.abeyy_path = str(Path(abeyy_path).resolve()) if abeyy_path else str(audio_paths["phone_distracted"])
        self.pani_pani_path = str(Path(pani_pani_path).resolve()) if pani_pani_path else str(audio_paths["drinking_water"])

    @property
    def muted(self) -> bool:
        return self.provider.muted

    @muted.setter
    def muted(self, val: bool) -> None:
        self.provider.muted = val

    @property
    def last_played(self) -> str:
        return self.provider.last_played

    def toggle_mute(self) -> bool:
        """Toggles audio mute status."""
        return self.provider.toggle_mute()

    def set_volume(self, level: float) -> None:
        """Sets playback volume between 0.0 and 1.0."""
        self.provider.set_volume(level)

    def play_book_closed(self, block: bool = False) -> bool:
        """Plays 'Kyu nahi ho rahi padhai' when user closes the book."""
        return self.play(self.kyu_nahi_path, "Kyu Nahi Ho Rahi Padhai?", block=block)

    def play_phone_distraction(self, block: bool = False) -> bool:
        """Plays 'Abeyy padhai likhai karo' when user starts using phone after book."""
        return self.play(self.abeyy_path, "Abeyy Padhai Likhai Karo!", block=block)

    def play_drinking_water(self, block: bool = False) -> bool:
        """Plays 'Pani pani' when user drinks water."""
        return self.play(self.pani_pani_path, "Pani Pani!", block=block)

    def play(self, audio_path: str | Path, track_title: Optional[str] = None, block: bool = False) -> bool:
        """Plays the specified audio file asynchronously or synchronously."""
        return self.provider.play(audio_path, track_title=track_title, block=block)

    def stop(self) -> None:
        """Stops any currently playing audio immediately."""
        self.provider.stop()
