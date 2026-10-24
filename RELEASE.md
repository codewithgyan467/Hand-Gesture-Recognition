# GestureOS — Release & Deployment Procedure

---

## 1. Versioning Scheme

GestureOS adheres to **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):
- **Current Version**: `1.0.0`
- **MAJOR**: Incompatible API or breaking behavioral/architecture changes.
- **MINOR**: Backwards-compatible new features, new gestures, or platform additions.
- **PATCH**: Backwards-compatible bug fixes, performance optimizations, or documentation.

---

## 2. Release Gate Checklist

Before creating a production release tag or distributable:

- [x] No hard-coded developer paths (`E:\...`, `C:\Users\...`) remain in codebase.
- [x] All 79 automated tests pass with exit code 0 (`python -m pytest GestureOS/tests`).
- [x] Clean startup without crashes or missing resource errors.
- [x] Clean shutdown without zombie threads or unreleased handles.
- [x] Zero-latency bounded camera queue verified (stale frames dropped).
- [x] Fail-safe emergency stop verified: physical release of mouse buttons and held keys.
- [x] UI thread never blocked by vision inference or audio playback.
- [x] Lazy model loading verified: StudyGuard models consume zero memory when OFF.
- [x] Hardware detection and automatic performance tier assignment operational.
- [x] Configuration auto-recovery from corrupt JSON verified (`.corrupt.bak`).
- [x] Simulation Mode operational without hardware webcam.
- [x] Safe Mode operational without OS automation actions.
- [x] Diagnostic export operational (clean JSON, no camera imagery).
- [x] Standalone PyInstaller compilation verified.

---

## 3. Production Packaging Procedure (Windows Standalone)

To compile the standalone distributable:

```cmd
cd "e:\Hand Gesture Recognition"
BUILD_DISTRIBUTABLE.bat
```

The build script:
1. Verifies PyInstaller in the active Python environment.
2. Compiles `GestureOS/run_gestureos.py` using `GestureOS/gestureos.spec`.
3. Packages neural models:
   - `models/hand_landmarker.task`
   - `models/efficientdet_lite0.tflite`
   - `models/blaze_face_short_range.tflite`
4. Bundles audio assets from `meme audios/*.mp3`.
5. Bundles pre-configured profiles from `profiles/*.json`.
6. Generates portable binary in `GestureOS/dist/GestureOS/GestureOS.exe`.

---

## 4. Distributable Verification

To verify the compiled release bundle:
1. Navigate to `GestureOS/dist/GestureOS/`.
2. Run `GestureOS.exe --diagnostics`.
3. Confirm that models and audio assets are found and verified.
4. Run `GestureOS.exe --simulation`.
5. Verify camera simulation and gesture dispatch.
