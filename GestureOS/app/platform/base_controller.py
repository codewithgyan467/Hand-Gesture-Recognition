"""Abstract Base OS Controller for cross-platform hardware automation."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional


class BaseOSController(ABC):
    """Abstract interface defining all operating system automation actions."""

    # --- Mouse & Pointer ---
    @abstractmethod
    def move_cursor(self, x: int, y: int) -> None:
        """Moves cursor to absolute screen coordinates (x, y)."""
        pass

    @abstractmethod
    def left_click(self) -> None:
        """Executes a single left mouse click."""
        pass

    @abstractmethod
    def right_click(self) -> None:
        """Executes a single right mouse click."""
        pass

    @abstractmethod
    def double_click(self) -> None:
        """Executes a double left mouse click."""
        pass

    @abstractmethod
    def mouse_down(self, button: str = "left") -> None:
        """Presses and holds the specified mouse button ('left' or 'right')."""
        pass

    @abstractmethod
    def mouse_up(self, button: str = "left") -> None:
        """Releases the held mouse button ('left' or 'right')."""
        pass

    @abstractmethod
    def scroll(self, dx: int, dy: int) -> None:
        """Scrolls vertically by dy and horizontally by dx."""
        pass

    @abstractmethod
    def get_cursor_position(self) -> Tuple[int, int]:
        """Returns the current cursor position (x, y)."""
        pass

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Returns the primary screen dimensions (width, height)."""
        pass

    # --- Audio & Volume ---
    @abstractmethod
    def set_volume(self, level_percent: float) -> None:
        """Sets master system volume percentage (0.0 to 100.0)."""
        pass

    @abstractmethod
    def get_volume(self) -> float:
        """Gets current master volume percentage (0.0 to 100.0)."""
        pass

    @abstractmethod
    def volume_up(self, step_percent: float = 4.0) -> None:
        """Increases volume by step_percent."""
        pass

    @abstractmethod
    def volume_down(self, step_percent: float = 4.0) -> None:
        """Decreases volume by step_percent."""
        pass

    @abstractmethod
    def volume_mute_toggle(self) -> None:
        """Toggles system audio mute."""
        pass

    # --- Media Playback ---
    @abstractmethod
    def media_play_pause(self) -> None:
        """Sends media Play/Pause toggle."""
        pass

    @abstractmethod
    def media_next(self) -> None:
        """Sends media Next track command."""
        pass

    @abstractmethod
    def media_previous(self) -> None:
        """Sends media Previous track command."""
        pass

    # --- Browser Control ---
    @abstractmethod
    def browser_back(self) -> None:
        """Navigates browser backward."""
        pass

    @abstractmethod
    def browser_forward(self) -> None:
        """Navigates browser forward."""
        pass

    @abstractmethod
    def browser_page_up(self) -> None:
        """Scrolls page up."""
        pass

    @abstractmethod
    def browser_page_down(self) -> None:
        """Scrolls page down."""
        pass

    @abstractmethod
    def browser_zoom_in(self) -> None:
        """Zooms into webpage."""
        pass

    @abstractmethod
    def browser_zoom_out(self) -> None:
        """Zooms out of webpage."""
        pass

    @abstractmethod
    def browser_new_tab(self) -> None:
        """Opens a new browser tab."""
        pass

    # --- Window Management ---
    @abstractmethod
    def window_switch_next(self) -> None:
        """Switches to the next application window."""
        pass

    @abstractmethod
    def window_switch_prev(self) -> None:
        """Switches to the previous application window."""
        pass

    @abstractmethod
    def window_minimize(self) -> None:
        """Minimizes the current active window."""
        pass

    @abstractmethod
    def window_maximize(self) -> None:
        """Maximizes or restores the current active window."""
        pass

    @abstractmethod
    def window_restore(self) -> None:
        """Restores window from maximized state."""
        pass

    # --- Presentation Mode ---
    @abstractmethod
    def presentation_next(self) -> None:
        """Advances to next slide."""
        pass

    @abstractmethod
    def presentation_prev(self) -> None:
        """Returns to previous slide."""
        pass

    @abstractmethod
    def presentation_start(self) -> None:
        """Starts presentation slideshow."""
        pass

    @abstractmethod
    def presentation_stop(self) -> None:
        """Exits slideshow."""
        pass

    # --- Generic Keyboard ---
    @abstractmethod
    def press_key(self, key: str) -> None:
        """Presses and releases a single key."""
        pass

    @abstractmethod
    def hotkey(self, *keys: str) -> None:
        """Executes a key combination sequentially pressed and released."""
        pass
