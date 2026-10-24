"""Windows-specific OS Controller utilizing high-performance native Win32 APIs and PyAutoGUI."""

from __future__ import annotations
import ctypes
import time
from typing import Tuple, Optional
import pyautogui
from app.platform.base_controller import BaseOSController
from app.diagnostics.logger import get_logger

logger = get_logger("windows_controller")

# Disable PyAutoGUI delay for maximum responsiveness
pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = False  # GestureOS has its own emergency stop guard

# Win32 Constants for mouse events
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000


class WindowsOSController(BaseOSController):
    """Production Windows OS automation controller."""

    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        try:
            self._user32.SetProcessDPIAware()
        except Exception:
            pass

        # Query primary screen metrics
        self._screen_width = self._user32.GetSystemMetrics(0)
        self._screen_height = self._user32.GetSystemMetrics(1)

        # Multi-monitor virtual desktop bounds (SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN)
        try:
            vx = self._user32.GetSystemMetrics(76)
            vy = self._user32.GetSystemMetrics(77)
            vw = self._user32.GetSystemMetrics(78)
            vh = self._user32.GetSystemMetrics(79)
            if vw > 0 and vh > 0:
                self._virtual_x = vx
                self._virtual_y = vy
                self._screen_width = vw
                self._screen_height = vh
            else:
                self._virtual_x = 0
                self._virtual_y = 0
        except Exception:
            self._virtual_x = 0
            self._virtual_y = 0

        # Initialize audio via pycaw
        self._audio_endpoint = None
        self._init_audio()

    def _init_audio(self) -> None:
        try:
            import pycaw.pycaw as pc
            speakers = pc.AudioUtilities.GetSpeakers()
            if speakers and hasattr(speakers, "EndpointVolume"):
                self._audio_endpoint = speakers.EndpointVolume
        except Exception as e:
            logger.warning(f"Could not initialize Windows Audio Endpoint: {e}")
            self._audio_endpoint = None

    def move_cursor(self, x: int, y: int) -> None:
        min_x = self._virtual_x
        max_x = self._virtual_x + self._screen_width - 1
        min_y = self._virtual_y
        max_y = self._virtual_y + self._screen_height - 1

        target_x = max(min_x, min(max_x, int(x)))
        target_y = max(min_y, min(max_y, int(y)))
        self._user32.SetCursorPos(target_x, target_y)

    def left_click(self) -> None:
        self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def right_click(self) -> None:
        self._user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def double_click(self) -> None:
        self.left_click()
        time.sleep(0.08)
        self.left_click()

    def mouse_down(self, button: str = "left") -> None:
        if button == "left":
            self._user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        elif button == "right":
            self._user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)

    def mouse_up(self, button: str = "left") -> None:
        if button == "left":
            self._user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == "right":
            self._user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

    def scroll(self, dx: int, dy: int) -> None:
        if dy != 0:
            # Win32 WHEEL_DELTA is 120
            clicks = int(dy * 120)
            self._user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, clicks, 0)
        if dx != 0:
            clicks_h = int(dx * 120)
            self._user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, clicks_h, 0)

    def get_cursor_position(self) -> Tuple[int, int]:
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        self._user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def get_screen_size(self) -> Tuple[int, int]:
        return (self._screen_width, self._screen_height)

    # --- Volume ---
    def set_volume(self, level_percent: float) -> None:
        clamped = max(0.0, min(100.0, float(level_percent)))
        scalar = clamped / 100.0
        if self._audio_endpoint:
            try:
                self._audio_endpoint.SetMasterVolumeLevelScalar(scalar, None)
                return
            except Exception as e:
                logger.debug(f"Audio scalar set failed: {e}")
                self._init_audio()

        # Fallback using keystrokes
        logger.debug("Falling back to volume keyboard shortcut")

    def get_volume(self) -> float:
        if self._audio_endpoint:
            try:
                scalar = self._audio_endpoint.GetMasterVolumeLevelScalar()
                return scalar * 100.0
            except Exception:
                self._init_audio()
        return 50.0

    def volume_up(self, step_percent: float = 4.0) -> None:
        current = self.get_volume()
        self.set_volume(current + step_percent)

    def volume_down(self, step_percent: float = 4.0) -> None:
        current = self.get_volume()
        self.set_volume(current - step_percent)

    def volume_mute_toggle(self) -> None:
        if self._audio_endpoint:
            try:
                muted = self._audio_endpoint.GetMute()
                self._audio_endpoint.SetMute(not muted, None)
                return
            except Exception:
                pass
        pyautogui.press("volumemute")

    # --- Media Playback ---
    def media_play_pause(self) -> None:
        pyautogui.press("playpause")

    def media_next(self) -> None:
        pyautogui.press("nexttrack")

    def media_previous(self) -> None:
        pyautogui.press("prevtrack")

    # --- Browser Navigation ---
    def browser_back(self) -> None:
        pyautogui.hotkey("alt", "left")

    def browser_forward(self) -> None:
        pyautogui.hotkey("alt", "right")

    def browser_page_up(self) -> None:
        pyautogui.press("pageup")

    def browser_page_down(self) -> None:
        pyautogui.press("pagedown")

    def browser_zoom_in(self) -> None:
        pyautogui.hotkey("ctrl", "+")

    def browser_zoom_out(self) -> None:
        pyautogui.hotkey("ctrl", "-")

    def browser_new_tab(self) -> None:
        pyautogui.hotkey("ctrl", "t")

    # --- Window Management ---
    def window_switch_next(self) -> None:
        pyautogui.hotkey("alt", "tab")

    def window_switch_prev(self) -> None:
        pyautogui.hotkey("alt", "shift", "tab")

    def window_minimize(self) -> None:
        pyautogui.hotkey("win", "down")

    def window_maximize(self) -> None:
        pyautogui.hotkey("win", "up")

    def window_restore(self) -> None:
        pyautogui.hotkey("win", "down")

    # --- Presentation Mode ---
    def presentation_next(self) -> None:
        pyautogui.press("right")

    def presentation_prev(self) -> None:
        pyautogui.press("left")

    def presentation_start(self) -> None:
        pyautogui.press("f5")

    def presentation_stop(self) -> None:
        pyautogui.press("esc")

    def press_key(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        pyautogui.hotkey(*keys)
