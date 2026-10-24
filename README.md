# GestureOS + StudyGuard
### Universal Local Touchless Desktop Interaction Platform + Focus Assistant

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-green.svg)]()
[![Vision](https://img.shields.io/badge/Vision-Google%20MediaPipe%20Tasks-orange.svg)]()
[![UI](https://img.shields.io/badge/UI-PySide6%20Qt%206-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-79%2F79%20Passed%20(100%25)-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)]()

**GestureOS** is a production-ready, low-latency, offline-first computer vision desktop platform. It transforms standard webcams into high-precision, touchless human-computer interfaces, bundled with **StudyGuard**, an intelligent focus and hydration assistant.

---

## 🚀 Key Capabilities

- **Fluid Touchless Mouse**: Low-jitter cursor guidance via adaptive **One Euro Filtering**, scale-invariant pinch clicking, movement-based dragging, and two-finger scrolling.
- **Dedicated Interaction Modes**: Mouse, Media (Spotify/YouTube/VLC), Browser, Presentation (Slides/Laser Pointer), Window Management, and Air Drawing with vector SVG / PNG export.
- **Intelligent StudyGuard Assistant**: Local object and face detection monitoring book closures, phone distractions, and hydration habits with customizable meme audio alerts.
- **Platform Abstraction Layer**: Native Win32 ctypes & CoreAudio on Windows, PyAutoGUI & amixer on Linux (X11/Wayland), and Quartz & osascript on macOS.
- **Fail-Safe Safety First**: Central `SafetyController` guaranteeing immediate physical release of held mouse buttons (`mouse_up`) and keyboard keys upon emergency stop (`ESC` key, Dual Fists gesture, or UI button).
- **Multi-Rate Vision Decimation**: Decouples 30 FPS hand tracking from heavier StudyGuard models (6–15 FPS) across 4 automatic hardware performance tiers (`FULL`, `BALANCED`, `LIGHT`, `COMPATIBILITY`).
- **100% Local-First Privacy**: Zero cloud uploads, zero telemetry, and zero camera frame persistence.
- **Self-Healing Configuration**: Automatic recovery and backup (`.corrupt.bak`) for corrupted or malformed settings files.

---

## 📋 Architectural Data Flow

```
WEBCAM / SIMULATION CAMERA
          │ (RGB Frame)
          ▼
CAMERA ENGINE (Zero-latency bounded 1-frame queue, auto-reconnect)
          │
          ▼
VISION DETECTOR (MediaPipe Tasks HandLandmarker — 21 3D Landmarks)
          │
          ├── LANDMARK NORMALIZER (Palm-scale invariant, aspect-ratio corrected)
          ├── STATIC DETECTOR (Pointer, Pinch, Fist, Peace, Thumbs Up/Down)
          ├── DYNAMIC ENGINE (Trajectory velocity buffer: Swipes, Waves, Circles)
          └── CUSTOM ML CLASSIFIER (Lightweight Scikit-Learn Model)
          │
          ▼
TEMPORAL VALIDATOR & DEBOUNCE (Hysteresis, confirmation frames, cooldowns)
          │
          ▼
MULTI-RATE STUDYGUARD (Lazy-loaded; EfficientDet-Lite0 + BlazeFace)
          │ (Decimated inference: 10 FPS; cached between frames)
          ▼
GESTURE STATE MACHINE (Inactive ➜ Activating ➜ Active ➜ Emergency Stop)
          │
          ▼
INTERACTION MODE MANAGER (Mouse, Media, Browser, Presentation, Drawing, Window)
          │
          ▼
ACTION DISPATCHER & SAFETY GOVERNOR (Cooldowns, safe mode, input release)
          │
          ▼
PLATFORM CONTROLLER (Win32 ctypes, X11/Wayland, macOS Quartz, Mock Controller)
          │
          ▼
PYSIDE6 DASHBOARD (Camera preview, HUD, Quick Controls, Settings, Diagnostics)
```

---

## 🛠 Quick Start

### 1. Development Launch
```bash
# Standard Launch
python -m gestureos

# Or run directly:
python run_gestureos.py
```

### 2. Specialized Modes
```bash
# Start with StudyGuard AI Focus Monitor active:
python -m gestureos --study-guard

# Run without webcam (Simulation Mode):
python -m gestureos --simulation

# Run in Safe Mode (disables OS automation for safe testing):
python -m gestureos --safe-mode

# Export hardware and platform diagnostics to stdout:
python -m gestureos --diagnostics

# Restore clean factory configuration (with automatic backup):
python -m gestureos --reset-config
```

---

## 🖐 Gesture Vocabulary

| Gesture | Pose / Action | Mouse Mode | Media Mode | Presentation Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Pointer** | ☝️ Point index finger | Move cursor | Virtual pointer | Laser pointer |
| **Left Click** | 🤏 Pinch thumb + index (< 0.35s) | Left click | Select | Confirm |
| **Drag & Drop** | 🤏 Pinch and hold (> 0.35s), then move | Mouse drag | Drawing stroke | Grab |
| **Right Click** | ✊ Right-hand punch/fist or thumb + middle | Right click | Context menu | Menu |
| **Scroll Up** | 👍 Thumbs Up | Scroll Up | Volume Up (+3%) | Start Slides (F5) |
| **Scroll Down**| 👎 Thumbs Down | Scroll Down | Volume Down (-3%)| Next Slide |
| **Play/Pause** | ✌️ Peace Sign (V-shape) | Secondary action | Play / Pause toggle | Pause |
| **Next Track** | ➡️ Horizontal Swipe Right | Forward | Next Track | Next Slide |
| **Prev Track** | ⬅️ Horizontal Swipe Left | Backward | Previous Track | Previous Slide |
| **Emergency** | ✊✊ Dual Fists or `[ESC]` key | Emergency Stop | Emergency Stop | Emergency Stop |

---

## 🎯 StudyGuard Assistant

StudyGuard monitors your workstation locally without saving video:
- **Book Closed**: Plays *"Kyu nahi ho rahi padhai"*.
- **Phone Distraction**: Plays *"Abeyy padhai likhai karo"*.
- **Hydration Detected**: Plays *"Pani pani"*.

### Shortcuts
- `[Ctrl + Space]`: Pause / Resume touchless mouse.
- `[ESC]`: Emergency Stop.
- `[B]`: Simulate reading book.
- `[C]`: Simulate closing book.
- `[P]`: Simulate smartphone distraction.
- `[W]`: Simulate drinking water.
- `[M]`: Mute / Unmute meme audio.

---

## 🧪 Automated Testing Suite

All 79 tests validate real computer vision and platform behavior without mocked hardware inflation:

```bash
python -m pytest GestureOS/tests -v
```

```
============================= 79 passed in 10.67s =============================
```

Test coverage includes:
- Gesture detection & geometric landmarks
- State machine & activation hold progress
- Fail-safe emergency stop input release
- Camera bounded 1-frame queue & stale frame dropping
- Clean shutdown without zombie threads
- Corrupt configuration self-healing recovery
- Missing model & audio graceful degradation
- Hardware profiler & automatic performance tiering
- StudyGuard multi-rate decimation & state machine

---

## 📚 Documentation

- [User Guide](file:///e:/Hand%20Gesture%20Recognition/USER_GUIDE.md): End-user operations, setup wizard, and profiles.
- [Developer Guide](file:///e:/Hand%20Gesture%20Recognition/DEVELOPER_GUIDE.md): Codebase design, platform abstraction, and extension tutorials.
- [Troubleshooting Guide](file:///e:/Hand%20Gesture%20Recognition/TROUBLESHOOTING.md): Camera, audio, lighting, and recovery resolutions.
- [Architecture](file:///e:/Hand%20Gesture%20Recognition/ARCHITECTURE.md): Multi-rate concurrency and state machine specification.
- [Release Procedure](file:///e:/Hand%20Gesture%20Recognition/RELEASE.md): Semantic versioning, build checklist, and PyInstaller distributable compilation.

---

## 📦 Standalone Distributable Build

To build the standalone Windows executable:
```cmd
BUILD_DISTRIBUTABLE.bat
```
Output: `GestureOS/dist/GestureOS/GestureOS.exe`.
