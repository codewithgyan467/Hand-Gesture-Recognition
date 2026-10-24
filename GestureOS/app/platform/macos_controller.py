"""macOS Controller utilizing PyAutoGUI and AppleScript (osascript) fallbacks."""

from __future__ import annotations
import sys
import subprocess
from typing import Tuple, Optional
import pyautogui
from app.platform.base_controller import BaseOSController
from app.diagnostics.logger import get_logger

logger = get_logger("macos_controller")

pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = False


class MacOSController(BaseOSController):
    """Production macOS automation controller with Retina display scaling and osascript volume."""

    def __init__(self) -> None:
        try:
            self._screen_width, self._screen_height = pyautogui.size()
        except Exception:
            self._screen_width, self._screen_height = 1920, 1080
        self._current_volume: float = 50.0

    def move_cursor(self, x: int, y: int) -> None:
        target_x = max(0, min(self._screen_width - 1, int(x)))
        target_y = max(0, min(self._screen_height - 1, int(y)))
        pyautogui.moveTo(target_x, target_y)

    def left_click(self) -> None:
        pyautogui.click(button="left")

    def right_click(self) -> None:
        pyautogui.click(button="right")

    def double_click(self) -> None:
        pyautogui.doubleClick(button="left")

    def mouse_down(self, button: str = "left") -> None:
        pyautogui.mouseDown(button=button)

    def mouse_up(self, button: str = "left") -> None:
        pyautogui.mouseUp(button=button)

    def scroll(self, dx: int, dy: int) -> None:
        if dy != 0:
            pyautogui.scroll(int(dy * 15))

    def get_cursor_position(self) -> Tuple[int, int]:
        pos = pyautogui.position()
        return (pos.x, pos.y)

    def get_screen_size(self) -> Tuple[int, int]:
        return (self._screen_width, self._screen_height)

    def set_volume(self, level_percent: float) -> None:
        self._current_volume = max(0.0, min(100.0, level_percent))
        vol_7 = int((self._current_volume / 100.0) * 7)
        try:
            subprocess.run(["osascript", "-e", f"set volume {vol_7}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass

    def get_volume(self) -> float:
        return self._current_volume

    def volume_up(self, step_percent: float = 4.0) -> None:
        self.set_volume(self._current_volume + step_percent)

    def volume_down(self, step_percent: float = 4.0) -> None:
        self.set_volume(self._current_volume - step_percent)

    def volume_mute_toggle(self) -> None:
        try:
            subprocess.run(["osascript", "-e", "set volume output muted not (output muted of (get volume settings))"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass

    def media_play_pause(self) -> None:
        pyautogui.press("playpause")

    def media_next(self) -> None:
        pyautogui.press("nexttrack")

    def media_previous(self) -> None:
        pyautogui.press("prevtrack")

    def browser_back(self) -> None:
        pyautogui.hotkey("command", "[")

    def browser_forward(self) -> None:
        pyautogui.hotkey("command", "]")

    def browser_page_up(self) -> None:
        pyautogui.press("pageup")

    def browser_page_down(self) -> None:
        pyautogui.press("pagedown")

    def browser_zoom_in(self) -> None:
        pyautogui.hotkey("command", "+")

    def browser_zoom_out(self) -> None:
        pyautogui.hotkey("command", "-")

    def browser_new_tab(self) -> None:
        pyautogui.hotkey("command", "t")

    def window_switch_next(self) -> None:
        pyautogui.hotkey("command", "tab")

    def window_switch_prev(self) -> None:
        pyautogui.hotkey("command", "shift", "tab")

    def window_minimize(self) -> None:
        pyautogui.hotkey("command", "m")

    def window_maximize(self) -> None:
        pyautogui.hotkey("command", "ctrl", "f")

    def window_restore(self) -> None:
        pyautogui.hotkey("command", "ctrl", "f")

    def presentation_next(self) -> None:
        pyautogui.press("right")

    def presentation_prev(self) -> None:
        pyautogui.press("left")

    def presentation_start(self) -> None:
        pyautogui.hotkey("command", "shift", "enter")

    def presentation_stop(self) -> None:
        pyautogui.press("escape")

    def press_key(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        pyautogui.hotkey(*keys)
