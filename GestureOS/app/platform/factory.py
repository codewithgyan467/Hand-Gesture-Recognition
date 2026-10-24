"""Platform controller factory selecting and initializing OS-specific drivers."""

from __future__ import annotations
import sys
from app.platform.base_controller import BaseOSController
from app.platform.mock_controller import MockOSController
from app.platform.capabilities import PlatformCapabilities, detect_platform_capabilities
from app.diagnostics.logger import get_logger

logger = get_logger("platform_factory")


def get_platform_controller(
    use_mock: bool = False, screen_width: int = 1920, screen_height: int = 1080
) -> BaseOSController:
    """Instantiates the appropriate OS automation controller for the current host environment."""
    if use_mock:
        logger.info("Instantiating MockOSController for simulation/testing.")
        return MockOSController(screen_width, screen_height)

    # Windows
    if sys.platform == "win32":
        try:
            from app.platform.windows_controller import WindowsOSController
            return WindowsOSController()
        except Exception as e:
            logger.error(f"Failed to initialize WindowsOSController: {e}. Falling back to MockOSController.")
            return MockOSController(screen_width, screen_height)

    # Linux
    elif sys.platform.startswith("linux"):
        try:
            from app.platform.linux_controller import LinuxOSController
            return LinuxOSController()
        except Exception as e:
            logger.error(f"Failed to initialize LinuxOSController: {e}. Falling back to MockOSController.")
            return MockOSController(screen_width, screen_height)

    # macOS
    elif sys.platform == "darwin":
        try:
            from app.platform.macos_controller import MacOSController
            return MacOSController()
        except Exception as e:
            logger.error(f"Failed to initialize MacOSController: {e}. Falling back to MockOSController.")
            return MockOSController(screen_width, screen_height)

    # Unknown platform fallback
    logger.warning(f"Unsupported operating system: {sys.platform}. Using MockOSController.")
    return MockOSController(screen_width, screen_height)
