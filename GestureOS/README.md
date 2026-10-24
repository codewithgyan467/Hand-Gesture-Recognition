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

## 🛠 Quick Start

```bash
# Standard Launch
python -m gestureos

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

## 🧪 Automated Testing Suite

```bash
python -m pytest tests -v
```

All 79 unit, integration, and platform fallback tests pass with exit code 0.
