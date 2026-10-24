# GestureOS + StudyGuard — Troubleshooting & Diagnostic Guide

This guide details resolutions for common setup, hardware, camera, audio, and configuration issues.

---

## 1. Quick Diagnostic Checklist

Run the built-in diagnostic command:
```bash
python -m gestureos --diagnostics
```
This inspects CPU, RAM, GPU, display, camera, models, and audio assets, outputting a complete health report.

Alternatively, in the UI:
Click **📊 Diagnostics** in the footer and select **📥 Export Diagnostic Report** to export a technical report (no camera images).

---

## 2. Common Issues & Solutions

### A. Camera Fails to Open or Disconnects

**Symptoms**: Status badge displays *"Ready: Waiting for Hand"* indefinitely or camera feed is black.

**Causes & Solutions**:
1. **Wrong Camera Index**:
   - If using an external USB webcam, camera index 0 may be the built-in laptop camera.
   - Go to **Settings → Camera** and select camera index 1 or 2, or use CLI flag:
     ```bash
     python -m gestureos --camera 1
     ```
2. **Camera In Use by Another Application**:
   - Close Zoom, Microsoft Teams, Skype, or browser tabs accessing the webcam.
3. **Windows Camera Privacy Permissions**:
   - Open **Windows Settings → Privacy & Security → Camera**.
   - Ensure *"Let desktop apps access your camera"* is enabled.
4. **Auto-Reconnect**:
   - GestureOS includes an automatic reconnection daemon. If the USB cable is bumped or re-plugged, GestureOS automatically recovers within 2 seconds without restarting.

---

### B. High Latency or Low Frame Rate

**Symptoms**: Camera preview is choppy or cursor lags behind hand movements.

**Causes & Solutions**:
1. **Performance Tier Misconfiguration**:
   - By default, GestureOS automatically selects the best tier based on logical CPU cores and available RAM.
   - If running on a lightweight laptop or battery saver mode, go to **Settings → Performance** and switch tier to **LIGHT** or **COMPATIBILITY**.
   - In LIGHT tier, StudyGuard inference frequency is decimated to preserve rock-steady 30 FPS camera preview.
2. **Room Lighting**:
   - Poor lighting causes webcam sensors to increase exposure time, dropping hardware frame rate below 15 FPS. Ensure adequate front-facing ambient lighting.
3. **Unbounded Queues Disabled**:
   - GestureOS enforces a zero-latency bounded 1-frame queue. Older frames are dropped immediately if inference takes longer than capture intervals.

---

### C. Sticky Drag or Cursor Moving Erratically

**Symptoms**: Mouse keeps dragging after releasing pinch or cursor jumps.

**Causes & Solutions**:
1. **Immediate Emergency Stop**:
   - Press **`[ESC]`** or show **Dual Fists (`✊✊`)** to immediately disengage control and release all physical mouse buttons and keys.
2. **Hand Calibration & Invert Horizontal**:
   - If moving right moves the cursor left, check **"Invert Horizontal (Mirror Fix)"** in the camera controls toolbar or Settings dialog.
3. **Active Region Reach**:
   - You do not need to move your hand across the entire room. GestureOS maps an inner 70% active bounding box to your full desktop, allowing comfortable small movements to reach all screen corners.
4. **Smoothing Preset**:
   - Switch Pointer Smoothing preset in the dashboard from *Fast* to **Balanced (Default)** or **Precise**.

---

### D. Missing or Corrupt Configuration

**Symptoms**: Application displays a warning about invalid configuration settings.

**Automatic Recovery**:
- GestureOS contains built-in self-healing configuration recovery:
  1. The corrupt file is automatically backed up as `<config_name>.corrupt.bak`.
  2. Clean default settings are created automatically.
  3. Startup proceeds without crashing.
- To manually reset configuration at any time:
  ```bash
  python -m gestureos --reset-config
  ```

---

### E. Missing Meme Audio Alerts

**Symptoms**: StudyGuard detects book close or phone distraction, but no audio plays.

**Causes & Solutions**:
1. **Mute Mode Active**:
   - Check the audio button on the StudyGuard card. Press **`[M]`** to unmute.
2. **Missing MP3 Files**:
   - StudyGuard checks for audio files in `meme audios/`:
     - `kyu-nahi-ho-rahi-padhai.mp3`
     - `abeyy-padhai-likhai-karo.mp3`
     - `pani pani.mp3`
   - If an audio file is missing, GestureOS **never crashes**. It displays a visual alert badge and logs the notice gracefully.
3. **Audio Output Device**:
   - On Windows, GestureOS uses the low-latency native Windows MCI subsystem (`winmm.dll`). Ensure your Windows default audio output device is connected and volume is turned up.

---

### F. Safe Mode Recovery

If GestureOS ever encounters an unhandled driver issue or unexpected third-party interference:
```bash
python -m gestureos --safe-mode
```
Safe Mode disables all virtual mouse/keyboard OS injection while allowing camera preview, calibration, diagnostics, and configuration editing.
