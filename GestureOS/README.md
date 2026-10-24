# GestureOS
### AI-Powered Touchless Human-Computer Interface

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011%20%7C%20Cross--Platform%20Ready-green.svg)]()
[![MediaPipe](https://img.shields.io/badge/Vision-Google%20MediaPipe%20Tasks-orange.svg)]()
[![UI](https://img.shields.io/badge/UI-PySide6%20Qt-purple.svg)]()
[![Tests](https://img.shields.io/badge/Tests-27%2F27%20Passed-brightgreen.svg)]()

GestureOS is a production-grade, low-latency, privacy-first computer vision platform that transforms any standard PC or laptop webcam into an intuitive, touchless human-computer interface.

---

## 1. Architectural Pipeline

GestureOS enforces strict architectural modularity across all layers:

```
WEBCAM / SIMULATION CAMERA
          │ (RGB Frame)
          ▼
    CAMERA ENGINE (Auto-reconnect, FPS limiter, Thread-safe capture)
          │
          ▼
    VISION DETECTOR (MediaPipe Tasks HandLandmarker - 21 3D Landmarks)
          │
          ▼
    LANDMARK NORMALIZER (Palm-scale invariant, aspect-ratio corrected)
          │
          ├── STATIC DETECTOR (Pointer, Pinch, Fist, Open Palm, Scroll)
          ├── DYNAMIC ENGINE (Temporal velocity buffer: Swipes, Waves, Circles)
          └── CUSTOM ML CLASSIFIER (Lightweight Scikit-Learn Model)
          │
          ▼
    TEMPORAL VALIDATOR & DEBOUNCE (Hysteresis, Consecutive frames, Cooldowns)
          │
          ▼
    GESTURE STATE MACHINE (Inactive -> Activating -> Active -> Executing -> Cooldown)
          │
          ▼
    INTERACTION MODE ENGINE (Mouse, Media, Browser, Presentation, Window, Drawing)
          │
          ▼
    ACTION DISPATCHER (Rate-limited, privileged safety filtering)
          │
          ▼
    PLATFORM OS CONTROLLER (Native Win32 APIs, PyCAW, or Mock Test Controller)
          │
          ▼
    MODERN DESKTOP DASHBOARD (PySide6, Live HUD, Diagnostics, Calibration)
```

---

## 2. Gesture Reference & Action Mapping

| Gesture | Pose / Motion | Action in Mouse Mode | Action in Media / Other Modes |
| :--- | :--- | :--- | :--- |
| **Pointer** | ☝️ Index extended | Move cursor | Virtual laser pointer |
| **Left Click** | 🤏 Thumb + Index pinch | Single left click | Confirm / Select |
| **Right Click** | 🤏 Thumb + Middle pinch | Context menu / Right click | Back |
| **Drag & Drop** | 🤏 Pinch + Hold (>350ms) | Mouse drag | Drawing stroke |
| **Double Click** | 🤏 Pinch tap twice within 400ms | Double click | Fullscreen toggle |
| **Scroll** | ✌️ Two fingers together | Smooth vertical scroll | Page scroll |
| **Pause** | ✊ Closed Fist | Pauses tracking | Mute / Pause |
| **Activation** | ✋ Open Palm held for 1.0s | Arms GestureOS | Play / Pause toggle |
| **Emergency Stop**| ✊✊ Dual Fists or `ESC` key | Instant global safety lock | Instant global safety lock |
| **Swipe Right** | ➡️ Fast horizontal motion | Forward / Next | Next track / Next slide |
| **Swipe Left** | ⬅️ Fast horizontal motion | Backward / Previous | Previous track / Previous slide |
| **Swipe Up/Down**| ⬆️ / ⬇️ Vertical motion | Page Up / Down | Window Maximize / Minimize |
| **Mode Switch** | ✌️ Peace / V-shape held 1.2s | Cycles to next mode | Cycles to next mode |

---

## 3. Interaction Modes

1. **Mouse Mode**: Low-jitter pointer tracking via the **One Euro Filter**, scale-invariant pinch-clicking, dragging, and dual-finger scrolling.
2. **Media Mode**: Touchless Spotify/YouTube/media controls with horizontal swipes for tracks and continuous thumb-index aperture distance mapping for master volume (0–100%).
3. **Browser Mode**: Swipes for Back/Forward, Page Up/Down, and Peace gesture for New Tab.
4. **Presentation Mode**: Next/Previous slide triggers tuned specifically for PowerPoint, Keynote, and Google Slides with an integrated laser pointer.
5. **Window Mode**: Task management (Alt+Tab switching, minimize, and restore).
6. **Air Drawing Mode**: Virtual canvas tracking fingertip trajectory with undo, redo, stroke width adjustments, eraser, and PNG export.
7. **Custom Mode**: User-defined mappings backed by lightweight Scikit-Learn classifiers.

---

## 4. Safety & False-Positive Prevention

- **Passive by Default**: The webcam tracks for visual HUD feedback, but OS actions remain disabled until the user holds an **Open Palm for 1.0 second**.
- **Global Emergency Stop**: Pressing the `ESC` key or showing **Dual Fists** instantly locks all mouse, keyboard, and OS commands.
- **Hysteresis & Cooldowns**:
  - Pinch threshold: activates at `dist <= 0.28`, releases at `dist >= 0.36`.
  - Click debounce: 220 ms.
  - Swipe cooldown: 500 ms.
  - Volume rate limiter: max 15 Hz to prevent command flooding.
- **Privileged Command Guard**: Whitelists authorized system tools and blocks arbitrary shell piping (`|`, `&&`, `;`).

---

## 5. Interactive 8-Step Calibration Wizard

Accessible directly from the dashboard:
1. **Camera Positioning**: Validates frame centering and lighting.
2. **Hand Detection**: Confirms 21-point tracking stability.
3. **Active Control Region**: Calibrates the user's natural motion boundaries.
4. **Cursor Range**: Maps active space to the primary monitor.
5. **Pinch Calibration**: Measures natural closed vs. open finger distances.
6. **Gesture Verification**: Interactive validation of all core poses.
7. **Sensitivity Tuning**: Select between Low, Medium, and High smoothing.
8. **Final Test Playground**: Safe dry-run testing before deployment.

---

## 6. Personal Profiles

Built-in profiles pre-tuned for distinct workflows:
- `Default`: Balanced smoothing and standard debounce.
- `Media`: High smoothing, high swipe sensitivity, media mode primary.
- `Gaming`: Low smoothing (sub-10ms response), high velocity limit.
- `Presentation`: Conservative swipe thresholds with presentation laser pointer.
- `Accessibility`: Forgiving thresholds, high jitter reduction, and slower timing.

---

## 7. Installation & Quickstart

### Prerequisites
- Python 3.12 (64-bit)
- Windows 10/11 (or macOS / Linux with mock controller)
- Any USB or integrated webcam

### Setup
```powershell
# Clone or navigate to repository root
cd GestureOS

# Create and activate Python 3.12 virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install audited dependencies
pip install -r requirements.txt
```

### Running GestureOS
```powershell
# Launch the full desktop application dashboard
python run_gestureos.py

# Launch in zero-risk Simulation Mode (synthetic camera, mock OS controller)
python run_gestureos.py --simulation

# Launch in Headless Mode (no GUI, ideal for servers/CI)
python run_gestureos.py --headless

# Select specific webcam or profile
python run_gestureos.py --camera 0 --profile Media
```

---

## 8. Verification & Test Suite

Run the full automated test suite (27 unit & integration tests):
```powershell
python -m pytest tests -v
```
All 27 tests validate:
- Landmark normalization invariance across distances and resolutions
- Angle and feature vector calculations
- Scale-invariant pinch hysteresis and drag timing
- Static and dynamic gesture recognition
- Temporal debounce and action cooldowns
- Cursor One Euro, EMA, and Kalman filter jitter suppression
- State machine transitions and emergency stop locking
- Action dispatching and rate limiting
- Config and profile persistence
- Complete end-to-end simulation pipeline execution
