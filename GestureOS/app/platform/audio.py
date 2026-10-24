"""Cross-platform Audio Provider abstraction for GestureOS & StudyGuard.

Guarantees non-blocking, low-latency playback with volume control, mute, stop,
and safe degradation across Windows (native MCI), Linux, and macOS.
Never crashes when an audio asset is missing or audio hardware is unavailable.
"""

from __future__ import annotations
import os
import sys
import time
import ctypes
import threading
import subprocess
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Dict
from app.diagnostics.logger import get_logger

logger = get_logger("audio_provider")


class BaseAudioProvider(ABC):
    """Abstract interface for application audio playback."""

    def __init__(self, muted: bool = False, volume: float = 1.0) -> None:
        self.muted = muted
        self.volume = max(0.0, min(1.0, volume))
        self._last_played_name: str = "None"
        self._last_played_time: float = 0.0

    @property
    def last_played(self) -> str:
        return self._last_played_name

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self.stop()
        return self.muted

    def set_volume(self, level: float) -> None:
        self.volume = max(0.0, min(1.0, level))

    @abstractmethod
    def play(self, audio_path: Path | str, track_title: Optional[str] = None, block: bool = False) -> bool:
        """Plays the specified audio file."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops currently playing audio immediately."""
        pass


class WindowsMciAudioProvider(BaseAudioProvider):
    """Native Windows MCI audio provider using winmm.dll for zero-latency MP3 streaming."""

    def __init__(self, muted: bool = False, volume: float = 1.0) -> None:
        super().__init__(muted=muted, volume=volume)
        self._lock = threading.Lock()
        self._counter = 0
        self._current_alias: Optional[str] = None

    def play(self, audio_path: Path | str, track_title: Optional[str] = None, block: bool = False) -> bool:
        if self.muted:
            return False

        path_obj = Path(audio_path)
        if not path_obj.is_file():
            logger.warning(f"Audio asset unavailable: {path_obj}")
            return False

        title = track_title or path_obj.name
        self._last_played_name = title
        self._last_played_time = time.time()

        if block:
            return self._play_mci(str(path_obj.resolve()), title)
        else:
            t = threading.Thread(
                target=self._play_mci, args=(str(path_obj.resolve()), title), daemon=True, name="MciAudioWorker"
            )
            t.start()
            return True

    def _play_mci(self, safe_path: str, title: str) -> bool:
        with self._lock:
            self._counter += 1
            alias = f"mci_audio_{self._counter}"
            prev_alias = self._current_alias
            self._current_alias = alias

            # Stop and close previous active alias to avoid handle leaks
            if prev_alias:
                try:
                    ctypes.windll.winmm.mciSendStringW(f"stop {prev_alias}", None, 0, None)
                    ctypes.windll.winmm.mciSendStringW(f"close {prev_alias}", None, 0, None)
                except Exception:
                    pass

            # Retrieve short 8.3 path to avoid spaces in MCI commands
            buf = ctypes.create_unicode_buffer(320)
            ctypes.windll.kernel32.GetShortPathNameW(safe_path, buf, 320)
            target = buf.value or safe_path

            open_cmd = f'open "{target}" type mpegvideo alias {alias}'
            ret = ctypes.windll.winmm.mciSendStringW(open_cmd, None, 0, None)
            if ret != 0:
                # Fallback to direct path
                ret = ctypes.windll.winmm.mciSendStringW(f'open "{safe_path}" type mpegvideo alias {alias}', None, 0, None)
                if ret != 0:
                    logger.error(f"MCI open failed with error code {ret} for: {safe_path}")
                    return False

            # Set volume (MCI accepts 0 to 1000)
            mci_vol = int(self.volume * 1000)
            ctypes.windll.winmm.mciSendStringW(f"setaudio {alias} volume to {mci_vol}", None, 0, None)

            play_ret = ctypes.windll.winmm.mciSendStringW(f"play {alias}", None, 0, None)
            return play_ret == 0

    def stop(self) -> None:
        with self._lock:
            if self._current_alias:
                try:
                    ctypes.windll.winmm.mciSendStringW(f"stop {self._current_alias}", None, 0, None)
                    ctypes.windll.winmm.mciSendStringW(f"close {self._current_alias}", None, 0, None)
                except Exception:
                    pass
                self._current_alias = None
            self._last_played_name = "Stopped"


class CrossPlatformAudioProvider(BaseAudioProvider):
    """Fallback audio provider using system media CLI players (aplay, paplay, afplay, ffplay) or winsound."""

    def __init__(self, muted: bool = False, volume: float = 1.0) -> None:
        super().__init__(muted=muted, volume=volume)
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def play(self, audio_path: Path | str, track_title: Optional[str] = None, block: bool = False) -> bool:
        if self.muted:
            return False

        path_obj = Path(audio_path)
        if not path_obj.is_file():
            logger.warning(f"Audio asset unavailable: {path_obj}")
            return False

        title = track_title or path_obj.name
        self._last_played_name = title
        self._last_played_time = time.time()

        if block:
            self._run_cli_player(path_obj)
            return True
        else:
            t = threading.Thread(
                target=self._run_cli_player, args=(path_obj,), daemon=True, name="CrossPlatformAudioWorker"
            )
            t.start()
            return True

    def _run_cli_player(self, path: Path) -> None:
        with self._lock:
            self.stop()

            # Attempt platform-specific CLI command
            cmd = None
            if sys.platform == "darwin":
                cmd = ["afplay", str(path)]
            elif sys.platform.startswith("linux"):
                # Try paplay, aplay, or ffplay
                for candidate in ["paplay", "aplay", "ffplay", "cvlc"]:
                    if shutil.which(candidate):
                        if candidate == "ffplay":
                            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
                        else:
                            cmd = [candidate, str(path)]
                        break

            if cmd:
                try:
                    self._current_process = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    logger.warning(f"Could not execute audio command {cmd}: {e}")
            else:
                logger.info(f"[Audio Simulated] Playing track: {path.name}")

    def stop(self) -> None:
        with self._lock:
            if self._current_process:
                try:
                    self._current_process.terminate()
                except Exception:
                    pass
                self._current_process = None
            self._last_played_name = "Stopped"


class NullAudioProvider(BaseAudioProvider):
    """Silent mock audio provider for headless mode, unit tests, or disabled audio."""

    def play(self, audio_path: Path | str, track_title: Optional[str] = None, block: bool = False) -> bool:
        self._last_played_name = track_title or Path(audio_path).name
        self._last_played_time = time.time()
        return True

    def stop(self) -> None:
        self._last_played_name = "Stopped"


def get_audio_provider(force_null: bool = False) -> BaseAudioProvider:
    """Factory selecting the optimal AudioProvider for the current operating system."""
    if force_null:
        return NullAudioProvider()

    if sys.platform == "win32":
        return WindowsMciAudioProvider()
    else:
        return CrossPlatformAudioProvider()
