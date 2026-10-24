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
    parser.add_argument(
        "--study-guard",
        "--study",
        action="store_true",
        help="Start with Study Guard AI Meme Distraction & Hydration Monitor turned ON",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Run in Safe Mode (disables OS automation, allows configuration and diagnostics safely)",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Export diagnostic report and print hardware/platform summary to stdout",
    )
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Reset user configuration to clean defaults with automatic backup of corrupt/old settings",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    import logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(log_level=log_level)
    logger = get_logger("main")
    logger.info("Initializing GestureOS platform...")

    # Handle --reset-config
    if args.reset_config:
        from app.core.resources import ResourceManager
        cfg_file = ResourceManager.get_config_dir() / "config.json"
        if cfg_file.exists():
            backup_file = ResourceManager.get_config_dir() / f"config.backup.{int(time.time())}.json"
            cfg_file.rename(backup_file)
            logger.info(f"Existing config backed up to: {backup_file}")
        clean_cfg = GestureOSConfig()
        clean_cfg.save_to_file(str(cfg_file))
        logger.info("Clean default configuration restored successfully.")
        print(f"GestureOS configuration successfully reset. Backup saved to: {backup_file if 'backup_file' in locals() else 'None'}")
        return 0

    # Handle --diagnostics
    if args.diagnostics:
        from app.diagnostics.hardware import HardwareProfiler
        from app.platform.capabilities import PlatformCapabilities
        from app.core.resources import ResourceManager
        import json

        hw = HardwareProfiler.detect()
        caps = PlatformCapabilities.detect()
        models = ResourceManager.validate_models()
        audios = ResourceManager.validate_audio_assets()

        diag_summary = {
            "version": "1.0.0",
            "platform": caps.to_dict(),
            "hardware": hw.to_dict(),
            "models": models,
            "audio_assets": audios,
        }
        print("=== GESTUREOS DIAGNOSTIC REPORT ===")
        print(json.dumps(diag_summary, indent=2))
        return 0

    # Load profile
    profile_mgr = ProfileManager()
    config = profile_mgr.load_profile(args.profile)
    config.camera.camera_index = args.camera

    if args.study_guard:
        config.enable_study_guard = True
        logger.info("Study Guard enabled via command line flag.")

    if args.simulation:
        config.camera.simulation_mode = True
        logger.info("Simulation Mode enabled via command line flag.")

    # Initialize Master Engine with safe_mode support
    engine = GestureOSEngine(
        config=config,
        use_mock_controller=args.simulation or args.safe_mode,
        safe_mode=args.safe_mode,
    )

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
