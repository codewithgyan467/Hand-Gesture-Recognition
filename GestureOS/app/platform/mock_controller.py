"""Mock OS Controller for simulation mode, headless testing, and verification."""

from __future__ import annotations
import time
from typing import Tuple, List, Dict, Any
from app.platform.base_controller import BaseOSController


class MockOSController(BaseOSController):
    """Safely intercepts and logs OS actions without executing them on the actual OS."""

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.cursor_x = screen_width // 2
        self.cursor_y = screen_height // 2
        self.current_volume = 50.0
        self.is_muted = False
        self.mouse_buttons_held = set()
        self.action_history: List[Dict[str, Any]] = []

    def _record(self, action: str, **kwargs: Any) -> None:
        self.action_history.append({
            "action": action,
            "timestamp": time.time(),
            "params": kwargs,
        })

    def move_cursor(self, x: int, y: int) -> None:
        self.cursor_x = max(0, min(self.screen_width, x))
        self.cursor_y = max(0, min(self.screen_height, y))
        self._record("move_cursor", x=self.cursor_x, y=self.cursor_y)

    def left_click(self) -> None:
        self._record("left_click", x=self.cursor_x, y=self.cursor_y)

    def right_click(self) -> None:
        self._record("right_click", x=self.cursor_x, y=self.cursor_y)

    def double_click(self) -> None:
        self._record("double_click", x=self.cursor_x, y=self.cursor_y)

    def mouse_down(self, button: str = "left") -> None:
        self.mouse_buttons_held.add(button)
        self._record("mouse_down", button=button, x=self.cursor_x, y=self.cursor_y)

    def mouse_up(self, button: str = "left") -> None:
        self.mouse_buttons_held.discard(button)
        self._record("mouse_up", button=button, x=self.cursor_x, y=self.cursor_y)

    def scroll(self, dx: int, dy: int) -> None:
        self._record("scroll", dx=dx, dy=dy)

    def get_cursor_position(self) -> Tuple[int, int]:
        return (self.cursor_x, self.cursor_y)

    def get_screen_size(self) -> Tuple[int, int]:
        return (self.screen_width, self.screen_height)

    def set_volume(self, level_percent: float) -> None:
        self.current_volume = max(0.0, min(100.0, float(level_percent)))
        self._record("set_volume", level=self.current_volume)

    def get_volume(self) -> float:
        return self.current_volume

    def volume_up(self, step_percent: float = 4.0) -> None:
        self.set_volume(self.current_volume + step_percent)

    def volume_down(self, step_percent: float = 4.0) -> None:
        self.set_volume(self.current_volume - step_percent)

    def volume_mute_toggle(self) -> None:
        self.is_muted = not self.is_muted
        self._record("volume_mute_toggle", is_muted=self.is_muted)

    def media_play_pause(self) -> None:
        self._record("media_play_pause")

    def media_next(self) -> None:
        self._record("media_next")

    def media_previous(self) -> None:
        self._record("media_previous")

    def browser_back(self) -> None:
        self._record("browser_back")

    def browser_forward(self) -> None:
        self._record("browser_forward")

    def browser_page_up(self) -> None:
        self._record("browser_page_up")

    def browser_page_down(self) -> None:
        self._record("browser_page_down")

    def browser_zoom_in(self) -> None:
        self._record("browser_zoom_in")

    def browser_zoom_out(self) -> None:
        self._record("browser_zoom_out")

    def browser_new_tab(self) -> None:
        self._record("browser_new_tab")

    def window_switch_next(self) -> None:
        self._record("window_switch_next")

    def window_switch_prev(self) -> None:
        self._record("window_switch_prev")

    def window_minimize(self) -> None:
        self._record("window_minimize")

    def window_maximize(self) -> None:
        self._record("window_maximize")

    def window_restore(self) -> None:
        self._record("window_restore")

    def presentation_next(self) -> None:
        self._record("presentation_next")

    def presentation_prev(self) -> None:
        self._record("presentation_prev")

    def presentation_start(self) -> None:
        self._record("presentation_start")

    def presentation_stop(self) -> None:
        self._record("presentation_stop")

    def press_key(self, key: str) -> None:
        self._record("press_key", key=key)

    def hotkey(self, *keys: str) -> None:
        self._record("hotkey", keys=keys)

    def clear_history(self) -> None:
        self.action_history.clear()
