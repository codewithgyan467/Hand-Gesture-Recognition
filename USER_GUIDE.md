# GestureOS + StudyGuard — User Guide

Welcome to **GestureOS**, the universal local touchless desktop interaction platform with the optional **StudyGuard** intelligent focus and hydration assistant.

---

## 1. Quick Start

### Installation & Launch

1. **Prerequisites**: Python 3.10+ (or use the standalone pre-packaged executable on Windows).
2. **Launch Development Application**:
   ```bash
   python -m gestureos
   ```
   Or run directly from the workspace:
   ```bash
   python run_gestureos.py
   ```
3. **Simulation Mode (No Camera Required)**:
   ```bash
   python -m gestureos --simulation
   ```
4. **Safe Mode (Testing without OS Automation)**:
   ```bash
   python -m gestureos --safe-mode
   ```
5. **System Diagnostic Output**:
   ```bash
   python -m gestureos --diagnostics
   ```
6. **Reset Configuration to Factory Defaults**:
   ```bash
   python -m gestureos --reset-config
   ```

---

## 2. First-Run Setup Wizard

Upon first launch, or by clicking **🧙 Setup Wizard** in the footer, the 14-step setup wizard will guide you through:

1. **Welcome**: Introduction to local touchless interaction.
2. **Platform Detection**: Probing OS driver (Win32 / X11 / Wayland / Quartz).
3. **Hardware Capabilities**: Detecting CPU cores, RAM, GPU, and assigning performance tier.
4. **Camera Detection**: Selecting camera index and verifying 30 FPS capture.
5. **Model Validation**: Verifying MediaPipe HandLandmarker, EfficientDet-Lite0, and BlazeFace models.
6. **Audio Validation**: Checking meme audio files and running sound test.
7. **Privacy & Permissions**: Zero telemetry guarantee and input injection rights.
8. **Camera Preview**: Aligning webcam position with room lighting.
9. **Hand Calibration**: Choosing dominant hand (Right/Left) and active region reachability.
10. **Gesture Calibration**: Adjusting pinch click sensitivity.
11. **Cursor Calibration**: Fine-tuning tracking speed and One Euro smoothing.
12. **Test Gestures**: Interactive playground to practice basic poses.
13. **Save Profile**: Choosing starting profile (Default, Gaming, Media, Presentation, Accessibility, Study).
14. **Finish**: Ready to use.

---

## 3. Gesture Controls Reference

### Mouse Mode (Default)
| Gesture | Pose | Action |
| :--- | :--- | :--- |
| **Pointer** | ☝️ Point with index finger | Moves cursor fluidly across desktop |
| **Left Click** | 🤏 Quick tap of thumb + index (< 0.35s) | Single left mouse click |
| **Drag & Drop** | 🤏 Pinch and hold (> 0.35s), then move | Click-and-drag / text selection |
| **Right Click** | ✊ Right-hand punch/fist or thumb + middle | Right-click context menu |
| **Scroll Up** | 👍 Thumbs Up | Smooth vertical scroll up |
| **Scroll Down**| 👎 Thumbs Down | Smooth vertical scroll down |
| **Pause** | ✊ Closed Fist held steady | Temporarily locks cursor in place |
| **Emergency Stop** | ✊✊ Dual Fists or `[ESC]` key | Instant lock, releases mouse & keys |

### Media Mode
- **Thumbs Up 👍**: Increase master volume (+3% step).
- **Thumbs Down 👎**: Decrease master volume (-3% step).
- **Peace Sign ✌️**: Play / Pause toggle.
- **Swipe Right ➡️**: Next track.
- **Swipe Left ⬅️**: Previous track.

### Presentation Mode
- **Point ☝️**: Virtual laser pointer.
- **Swipe Right ➡️**: Next slide.
- **Swipe Left ⬅️**: Previous slide.
- **Thumbs Up 👍**: Start presentation (F5).
- **Closed Fist ✊**: Exit presentation (ESC).

### Browser Mode
- **Thumbs Up / Down 👍👎**: Page Up / Page Down.
- **Swipe Left / Right ⬅️➡️**: Browser Back / Forward.
- **Peace Sign ✌️**: Open new browser tab.

### Air Drawing Mode
- **Point ☝️**: Draw stroke on air canvas.
- **Pinch 🤏**: Grab / select stroke.
- **Peace Sign ✌️**: Toggle between Pen and Eraser.
- **Thumbs Up 👍**: Undo last stroke.
- **Thumbs Down 👎**: Redo stroke.
- **Toolbar**: Save as high-resolution PNG or vector SVG.

---

## 4. StudyGuard AI Focus & Hydration Assistant

StudyGuard monitors your study area using real-time local object and face detection models:

- **Book Closed Detection**: When you close your study book, StudyGuard plays the alert audio: *"Kyu nahi ho rahi padhai"*.
- **Phone Distraction**: If you put down your book and pick up a smartphone, StudyGuard plays: *"Abeyy padhai likhai karo"*.
- **Hydration Tracking**: When you drink water from a bottle or glass, StudyGuard plays: *"Pani pani"*.

### Hotkeys & Shortcuts
- `[Ctrl + Space]`: Toggle Touchless Mouse active / paused.
- `[ESC]`: Emergency Stop (instant fail-safe release of all mouse buttons and keys).
- `[B]`: Simulate reading book.
- `[C]`: Simulate closing book.
- `[P]`: Simulate smartphone distraction.
- `[W]`: Simulate drinking water.
- `[M]`: Mute / Unmute meme alert audio.

---

## 5. Built-in Profiles

GestureOS includes 8 dedicated, pre-calibrated workflow profiles:
1. **Default**: Balanced smoothing and natural responsiveness for everyday productivity.
2. **Gaming**: Ultra-low latency cursor ballistics with immediate response.
3. **Media**: Optimized for media players (VLC, YouTube, Spotify, Netflix).
4. **Presentation**: Tailored for PowerPoint, Google Slides, Keynote.
5. **Browser**: Navigation and reading mode with page scrolling.
6. **Accessibility**: Extra-smooth dampening, dwell clicking, and high-contrast visuals.
7. **Study**: StudyGuard enabled with distraction alerts and hydration monitoring.
8. **Custom**: Fully user-configurable mappings and thresholds.

Profiles can be exported, imported, renamed, and reset from the Settings dialog.

---

## 6. Privacy & Safety Guarantee

- **100% Offline**: Zero remote telemetry, cloud processing, or external network requests.
- **Transient Memory**: Camera frames are processed strictly in RAM and discarded immediately. No frames are ever written to disk or recorded.
- **Fail-Safe Emergency Stop**: Pressing `ESC` or performing dual fists immediately releases any physical mouse buttons or keys being simulated, preventing stuck mouse clicks or runaway inputs.
