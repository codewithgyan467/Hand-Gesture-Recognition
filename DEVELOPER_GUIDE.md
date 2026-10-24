# GestureOS + StudyGuard — Developer Guide

Welcome to the **GestureOS Developer Guide**. This document details the architectural contracts, design patterns, testing practices, and guidelines for extending the platform.

---

## 1. Architectural Philosophy

GestureOS is engineered under strict production principles:
- **Offline-First & Local-First**: No remote dependencies, external telemetry, or cloud processing.
- **Graceful Degradation**: Never crash when a hardware or OS feature is unavailable. Detect missing capabilities, inform the user with friendly guidance, and continue executing supported subsystems.
- **Zero-Latency Bounded Buffers**: Do not build queue latency. Drop stale capture frames immediately if inference takes longer than frame intervals.
- **Fail-Safe Safety First**: OS injection must guarantee physical release of held mouse buttons (`mouse_up("left")`) and keys upon emergency stop or tracking loss.
- **Multi-Rate Vision Inference**: Decouple high-frequency hand tracking (30 FPS) from heavier object and face detection models (10 FPS) through dynamic stride decimation.

---

## 2. Directory Structure

```
GestureOS/
├── app/
│   ├── actions/          # Intent execution, cooldowns, ActionDispatcher
│   ├── calibration/      # ProfileManager, personal calibration data
│   ├── camera/           # CameraProvider, OpenCVCamera (bounded thread), SimulationCamera
│   ├── core/             # Engine, state machine, config, performance controller, resources
│   ├── cursor/           # One Euro Filter, CursorEngine, dead zones, acceleration
│   ├── diagnostics/      # Hardware detection, telemetry collector, logging
│   ├── gestures/         # StaticDetector, DynamicDetector, TwoHandCoordinator, MLClassifier
│   ├── modes/            # Interaction modes: Mouse, Media, Browser, Presentation, Drawing
│   ├── platform/         # Platform abstraction layer: Windows, Linux, macOS, Mock
│   ├── safety/           # SafetyController, EmergencyStopGuard, ActivationGuard
│   ├── ui/               # PySide6 Qt GUI: main window, setup wizard, settings, diagnostics
│   └── vision/           # MediaPipe detectors, ModelManager (lazy loading), StudyGuard
├── models/               # Neural network task files (.task, .tflite)
├── meme audios/          # Audio feedback MP3 files
├── profiles/             # Pre-configured and user profiles (JSON)
└── tests/                # 79 Unit, Integration, and Hardware-Fallback tests
```

---

## 3. Platform Abstraction Layer

The platform abstraction layer isolates OS-specific code from core gesture logic.

### Base Interface: `BaseOSController` (`app/platform/base_controller.py`)
All platform implementations must implement:
- `move_cursor(x, y)`
- `left_click()`, `right_click()`, `double_click()`
- `mouse_down(button)`, `mouse_up(button)`
- `scroll(dx, dy)`
- `get_cursor_position()` -> `(x, y)`
- `get_screen_size()` -> `(w, h)`
- `set_volume(level)`, `volume_up(step)`, `volume_down(step)`, `volume_mute_toggle()`
- Media controls: `media_play_pause()`, `media_next()`, `media_previous()`
- Browser controls: `browser_back()`, `browser_forward()`, `browser_page_up()`, `browser_page_down()`, `browser_new_tab()`
- Window controls: `window_switch_next()`, `window_switch_prev()`, `window_minimize()`, `window_maximize()`, `window_restore()`
- Presentation controls: `presentation_start()`, `presentation_stop()`, `presentation_next()`, `presentation_prev()`
- Foreground window detection: `get_foreground_window_title()`

### Factory: `get_platform_controller(...)` (`app/platform/factory.py`)
Instantiates the appropriate controller based on host environment:
- Windows: `WindowsOSController` (Native Win32 ctypes & CoreAudio)
- Linux: `LinuxOSController` (PyAutoGUI, X11/Wayland, amixer)
- macOS: `MacOSController` (PyAutoGUI, Quartz, osascript)
- Simulation / Tests: `MockOSController` (In-memory event recording without OS mutations)

---

## 4. Multi-Rate Vision & Lazy Model Loading

### `ModelManager` (`app/vision/model_manager.py`)
- Hand tracking model (`hand_landmarker.task`) loads at startup.
- StudyGuard models (`efficientdet_lite0.tflite`, `blaze_face_short_range.tflite`) are **lazy-loaded**:
  - Consumes zero memory when StudyGuard is toggled OFF.
  - Calling `model_manager.unload_study_detector()` triggers garbage collection to immediately free RAM.

### `PerformanceController` (`app/core/performance.py`)
Dynamically adjusts inference frequency across 4 hardware performance tiers:
- **FULL**: 30 FPS camera, stride 1 hand tracking, stride 2 StudyGuard (15 FPS).
- **BALANCED**: 30 FPS camera, stride 1 hand tracking, stride 3 StudyGuard (10 FPS).
- **LIGHT**: 24 FPS camera, stride 1 hand tracking, stride 4 StudyGuard (6 FPS).
- **COMPATIBILITY**: 15 FPS camera, stride 2 hand tracking, stride 5 StudyGuard (3 FPS).

If latency exceeds the target budget across 15 consecutive frames, StudyGuard inference stride automatically throttles back to preserve rock-steady 30 FPS camera preview.

---

## 5. Adding New Gestures or Modes

### Adding a Static Gesture
1. Add gesture identifier to `GestureType` enum in `app/core/types.py`.
2. Implement geometric rule in `StaticGestureDetector.detect()` (`app/gestures/static_detector.py`) using angle / distance metrics from `HandFeatures`.
3. Add unit test in `tests/test_gestures.py` asserting correct recognition from landmark coordinates.

### Adding an Interaction Mode
1. Inherit from `BaseMode` in `app/modes/`.
2. Implement `process_gesture(gesture_result, landmarks, features, timestamp) -> Optional[ActionIntent]`.
3. Register new mode in `ModeManager._init_modes()` (`app/modes/mode_manager.py`).
4. Add unit test verifying intent dispatch.

---

## 6. Testing & QA

Run all tests via pytest:
```bash
python -m pytest GestureOS/tests -v
```

### Running Specific Test Suites
```bash
# Core gesture recognition
python -m pytest GestureOS/tests/test_gestures.py -v

# SafetyController & emergency stop
python -m pytest GestureOS/tests/test_platform_and_safety.py -v

# Portability and corrupt config recovery
python -m pytest GestureOS/tests/test_portability_and_resources.py -v

# StudyGuard state machine and detector
python -m pytest GestureOS/tests/test_study_guard.py -v

# Performance tiering and multi-rate decimation
python -m pytest GestureOS/tests/test_performance_and_tiering.py -v
```

---

## 7. Packaging Standalone Distributables

Compile standalone distributable executable using PyInstaller:
```bash
# Windows
.\BUILD_DISTRIBUTABLE.bat
```
Output files are placed in `GestureOS/dist/GestureOS/` with models, profiles, and sound assets bundled.
