"""Meme Audio Player using native Windows MCI for zero-latency, non-blocking playback."""

from __future__ import annotations
import os
import sys
import time
import ctypes
import threading
from typing import Optional, Dict


class MemeAudioPlayer:
    """Plays meme audio files asynchronously without stalling the computer vision loop."""

    # Default relative and absolute locations
    DEFAULT_KYU_NAHI = r"E:\Hand Gesture Recognition\meme audios\kyu-nahi-ho-rahi-padhai.mp3"
    DEFAULT_ABEYY = r"E:\Hand Gesture Recognition\meme audios\abeyy-padhai-likhai-karo.mp3"
    DEFAULT_PANI_PANI = r"E:\Hand Gesture Recognition\meme audios\pani pani.mp3"

    def __init__(
        self,
        kyu_nahi_path: Optional[str] = None,
        abeyy_path: Optional[str] = None,
        pani_pani_path: Optional[str] = None,
        muted: bool = False,
    ) -> None:
        self.muted = muted
        self._lock = threading.Lock()
        self._counter = 0
        self._current_alias: Optional[str] = None
        self._last_played_name: str = "None"
        self._last_played_time: float = 0.0

        # Resolve paths
        self.kyu_nahi_path = self._resolve_path(kyu_nahi_path or self.DEFAULT_KYU_NAHI, "kyu-nahi-ho-rahi-padhai.mp3")
        self.abeyy_path = self._resolve_path(abeyy_path or self.DEFAULT_ABEYY, "abeyy-padhai-likhai-karo.mp3")
        self.pani_pani_path = self._resolve_path(pani_pani_path or self.DEFAULT_PANI_PANI, "pani pani.mp3")

    def _resolve_path(self, target_path: str, filename_fallback: str) -> str:
        """Resolves target path whether absolute or relative to workspace."""
        if os.path.exists(target_path):
            return os.path.abspath(target_path)

        # Check relative to current working directory
        cwd_cand = os.path.abspath(os.path.join(os.getcwd(), "meme audios", filename_fallback))
        if os.path.exists(cwd_cand):
            return cwd_cand

        # Check relative to this file's root
        script_dir = os.path.abspath(os.path.dirname(__file__))
        root_cand = os.path.abspath(os.path.join(script_dir, "..", "..", "..", "meme audios", filename_fallback))
        if os.path.exists(root_cand):
            return root_cand

        return target_path

    @property
    def last_played(self) -> str:
        return self._last_played_name

    def toggle_mute(self) -> bool:
        """Toggles audio mute status."""
        self.muted = not self.muted
        if self.muted:
            self.stop()
        return self.muted

    def play_book_closed(self, block: bool = False) -> bool:
        """Plays 'Kyu nahi ho rahi padhai' when user closes the book."""
        return self.play(self.kyu_nahi_path, "Kyu Nahi Ho Rahi Padhai?", block=block)

    def play_phone_distraction(self, block: bool = False) -> bool:
        """Plays 'Abeyy padhai likhai karo' when user starts using phone after book."""
        return self.play(self.abeyy_path, "Abeyy Padhai Likhai Karo!", block=block)

    def play_drinking_water(self, block: bool = False) -> bool:
        """Plays 'Pani pani' when user drinks water."""
        return self.play(self.pani_pani_path, "Pani Pani!", block=block)

    def play(self, audio_path: str, track_title: Optional[str] = None, block: bool = False) -> bool:
        """Plays the specified audio file asynchronously."""
        if self.muted:
            return False

        if not os.path.exists(audio_path):
            print(f"[MemeAudioPlayer] Warning: Audio file not found at: {audio_path}")
            return False

        title = track_title or os.path.basename(audio_path)
        self._last_played_name = title
        self._last_played_time = time.time()

        if block:
            return self._play_mci(audio_path, title)
        else:
            t = threading.Thread(target=self._play_mci, args=(audio_path, title), daemon=True)
            t.start()
            return True

    def _play_mci(self, audio_path: str, title: str) -> bool:
        """Executes Windows MCI commands to stream MP3."""
        if sys.platform != "win32":
            # Non-windows fallback mock
            print(f"[MemeAudioPlayer Mock] Playing: {title}")
            return True

        with self._lock:
            self._counter += 1
            alias = f"meme_{self._counter}"
            prev_alias = self._current_alias
            self._current_alias = alias

            # Stop and close previous active alias
            if prev_alias:
                ctypes.windll.winmm.mciSendStringW(f"stop {prev_alias}", None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f"close {prev_alias}", None, 0, None)

            # Retrieve short 8.3 path to eliminate spaces/encoding issues
            buf = ctypes.create_unicode_buffer(320)
            ctypes.windll.kernel32.GetShortPathNameW(audio_path, buf, 320)
            safe_path = buf.value or audio_path

            open_cmd = f'open "{safe_path}" type mpegvideo alias {alias}'
            ret = ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, None)
            if ret != 0:
                # If short path fails, attempt direct double quoted path
                direct_cmd = f'open "{audio_path}" type mpegvideo alias {alias}'
                ret = ctypes.windll.winmm.mciSendStringW(direct_cmd, None, 0, None)
                if ret != 0:
                    print(f"[MemeAudioPlayer] MCI open failed with error code: {ret}")
                    return False

            play_ret = ctypes.windll.winmm.mciSendStringW(f"play {alias}", None, 0, None)
            return play_ret == 0

    def stop(self) -> None:
        """Stops any currently playing audio immediately."""
        with self._lock:
            if self._current_alias and sys.platform == "win32":
                ctypes.windll.winmm.mciSendStringW(f"stop {self._current_alias}", None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f"close {self._current_alias}", None, 0, None)
                self._current_alias = None
            self._last_played_name = "Stopped"
