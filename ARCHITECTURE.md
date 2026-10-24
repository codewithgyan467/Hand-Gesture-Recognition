# GestureOS + StudyGuard — Architectural Design Specification

---

## 1. System Overview

GestureOS is a modular, event-driven desktop platform providing:
1. **Touchless Human-Computer Interaction**: Real-time 21-point 3D hand tracking, dynamic One Euro filtering, scale-invariant pinch clicking, dragging, and gesture dispatching.
2. **StudyGuard Focus Assistant**: Multi-rate object and face detection monitoring study books, phone distractions, and hydration habits.
3. **Platform Abstraction Layer**: Operating system isolation supporting Windows (Win32, CoreAudio), Linux (PyAutoGUI, X11/Wayland), macOS (PyAutoGUI, Quartz), and Mock simulation.
4. **Safety & Fail-Safe Architecture**: State machine transitions, central safety governance, and immediate physical release of held mouse buttons and keys.

---

## 2. High-Level Data Flow

```
Camera Stream (OpenCV / DirectShow / Simulation)
  │ (Bounded 1-frame queue; stale frames dropped)
  ▼
GestureOSEngine
  ├── Step 1: HandDetector (MediaPipe Tasks - 21 3D Landmarks)
  │     ├── FeatureExtractor (Angles, distances, palm scale normalization)
  │     ├── StaticGestureDetector (Pointer, Pinch, Fist, Peace, Thumbs Up/Down)
  │     ├── DynamicGestureDetector (Trajectory velocity buffer: Swipes, Waves)
  │     ├── TwoHandCoordinator (Primary/Secondary role assignment, Dual Fists)
  │     └── TemporalValidator (Hysteresis, consecutive confirmation, debounce)
  │
  ├── Step 2: Multi-Rate StudyGuard (Adaptive Decimation via PerformanceController)
  │     ├── If stride matches: StudyVisionDetector (EfficientDet-Lite0 + BlazeFace)
  │     └── StudyStateMachine -> MemeAudioPlayer (Windows MCI / Cross-Platform Audio)
  │
  ├── Step 3: Interaction Mode Manager
  │     ├── Mouse Mode: CursorEngine (One Euro Filter + Deadzone + Active Region)
  │     ├── Media Mode: Play/Pause, Horizontal Swipes, Master Volume
  │     ├── Presentation Mode: Laser Pointer, Slide Navigation
  │     ├── Browser Mode: Page Navigation, Tab Management
  │     ├── Air Drawing Mode: Virtual Canvas, Vector SVG / PNG Export
  │     └── Window Mode: Task Switching & Window Management
  │
  ├── Step 4: SafetyController & ActionDispatcher
  │     ├── Validation against GestureStateMachine state (ACTIVE vs PASSIVE vs LOCKED)
  │     ├── Cooldown enforcement (Click 220ms, Swipes 500ms, Volume 66ms)
  │     └── Platform OS Controller execution (Virtual mouse, keystrokes)
  │
  └── Step 5: Qt/PySide6 UI Synchronization (30 Hz Tick)
        ├── CameraWidget (Low-overhead QImage rendering)
        ├── Status Badges, Dispatched Action Pill, FPS Counter
        └── System Tray Icon & Background Notifications
```

---

## 3. Concurrency & Threading Model

```
Thread 1: CameraCaptureWorker (Background daemon thread)
  • Continuously drains hardware video frames from cv2.VideoCapture.
  • Bounded buffer size = 1. Overwrites stale frames instantaneously.
  • Sets _new_frame_event.

Thread 2: GestureOSPipelineWorker (Engine processing thread)
  • Wakes up on frame arrival or target FPS interval timer.
  • Executes hand tracking, feature extraction, gesture validation, and mode processing.
  • Calls performance_controller.record_frame(latency_ms).
  • Emits PipelineFrameOutput to lock-free latest_output slot.

Thread 3: Qt Main UI Thread (PySide6 Event Loop)
  • Renders dashboard widgets, handles buttons, modals, and tray icon.
  • Periodically reads engine.latest_output at 30 Hz.
  • NEVER performs OpenCV capture or MediaPipe ML inference.

Thread 4: EmergencyKeyboardListener (pynput hook thread)
  • Monitors global ESC key press independently of window focus.
  • Direct call to safety_controller.trigger_emergency_stop().
```

---

## 4. Multi-Rate Vision Decimation

Running heavy object detection models on every frame introduces frame drops on lower-spec hardware. GestureOS decouples tracking frequencies:

| Subsystem | Frequency | Model | Rationale |
| :--- | :--- | :--- | :--- |
| **Webcam Capture** | 30 FPS | Hardware Sensor | Fluid real-time video feedback |
| **Hand Tracking** | 30 FPS | `hand_landmarker.task` | Instant, low-latency mouse response |
| **StudyGuard Detection** | 6–15 FPS | `efficientdet_lite0.tflite` + `blaze_face_short_range.tflite` | Behavioral states change over seconds, not milliseconds |
| **UI Rendering** | 30 FPS | Qt/PySide6 QPainter | Smooth 30 Hz dashboard visualization |

---

## 5. Safety Controller & Emergency Stop Contract

When an emergency stop trigger occurs (ESC key, Dual Fists gesture, UI Stop button, or Critical Exception):
1. State machine transitions immediately to `EMERGENCY_STOP` state.
2. `SafetyController.trigger_emergency_stop()` physically invokes:
   - `controller.mouse_up("left")`
   - `controller.mouse_up("right")`
   - Key releases for all tracked held keys.
3. All subsequent `ActionIntent` dispatches are rejected at `ActionDispatcher` level until user explicitly clears the emergency stop.
