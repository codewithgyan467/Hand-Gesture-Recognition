"""Entry point for GestureOS: AI-Powered Touchless Human-Computer Interface."""

from __future__ import annotations
import sys
import argparse
import time
from PySide6.QtWidgets import QApplication

from app.core.config import GestureOSConfig
from app.core.engine import GestureOSEngine
from app.ui.main_window import GestureOSMainWindow
from app.diagnostics.logger import setup_logger, get_logger
from app.calibration.profile_manager import ProfileManager


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GestureOS: Production AI Touchless Computer-Control Platform"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in zero-risk Simulation Mode (synthetic camera, mock OS controller)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam device index (default: 0)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="Default",
        help="Initial profile name (Default, Media, Gaming, Presentation, Accessibility)",
    )
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Launch first-time onboarding setup wizard on startup",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run engine headlessly without PySide6 GUI",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose DEBUG logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    import logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(log_level=log_level)
    logger = get_logger("main")
    logger.info("Initializing GestureOS platform...")

    # Load profile
    profile_mgr = ProfileManager()
    config = profile_mgr.load_profile(args.profile)
    config.camera.camera_index = args.camera

    if args.simulation:
        config.camera.simulation_mode = True
        logger.info("Simulation Mode enabled via command line flag.")

    # Initialize Master Engine
    engine = GestureOSEngine(config=config, use_mock_controller=args.simulation)

    if args.headless:
        logger.info("Starting GestureOS in HEADLESS mode (Ctrl+C to stop)...")
        engine.start()
        try:
            while True:
                time.sleep(1.0)
                snap = engine.telemetry.get_snapshot()
                logger.info(
                    f"Headless Status: State={snap.state} Mode={snap.current_mode} "
                    f"Gesture={snap.current_gesture} FPS={snap.fps:.1f} TotalGestures={snap.total_gestures}"
                )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down headless engine...")
        finally:
            engine.stop()
        return 0

    # Start PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName("GestureOS")
    app.setOrganizationName("GestureOS")

    window = GestureOSMainWindow(engine)
    window.show()

    # Start engine
    engine.start()

    if args.wizard:
        window.open_onboarding_wizard()

    logger.info("GestureOS UI ready.")
    exit_code = app.exec()
    engine.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
