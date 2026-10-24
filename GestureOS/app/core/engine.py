"""Master Pipeline Engine coordinating Camera, Vision, Gestures, State Machine, Modes, and Dispatcher."""

from __future__ import annotations
import time
import threading
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

from app.core.config import GestureOSConfig
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    GestureRecognitionResult,
    GestureType,
    GestureState,
    InteractionMode,
    ActionIntent,
    IntentType,
)
from app.core.state_machine import GestureStateMachine
from app.core.events import EventBus, EventType, default_event_bus
from app.camera.base import BaseCamera
from app.camera.cv_camera import OpenCVCamera
from app.camera.simulation_camera import SimulationCamera
from app.vision.detector import HandDetector
from app.vision.feature_extractor import FeatureExtractor
from app.vision.visualizer import DebugVisualizer
from app.cursor.cursor_engine import CursorEngine
from app.gestures.static_detector import StaticGestureDetector
from app.gestures.dynamic_detector import DynamicGestureDetector
from app.gestures.temporal_validator import TemporalValidator
from app.gestures.two_hand_engine import TwoHandCoordinator
from app.gestures.ml_classifier import CustomMLGestureClassifier
from app.safety.activation_guard import ActivationGuard
from app.safety.emergency_stop import EmergencyStopGuard
from app.modes.mode_manager import ModeManager
from app.actions.dispatcher import ActionDispatcher
from app.platform.base_controller import BaseOSController
from app.platform.windows_controller import WindowsOSController
from app.platform.mock_controller import MockOSController
from app.diagnostics.telemetry import TelemetryCollector, PerformanceSnapshot
from app.diagnostics.logger import get_logger
from app.vision.study_detector import StudyVisionDetector, StudyDetectionResult
from app.vision.study_state_machine import StudyStateMachine, StudyState
from app.vision.meme_audio_player import MemeAudioPlayer

logger = get_logger("engine")


@dataclass
class PipelineFrameOutput:
    annotated_frame: np.ndarray
    raw_frame: np.ndarray
    hands: List[HandLandmarks]
    features: Optional[HandFeatures]
    gesture: str
    confidence: float
    state: str
    mode: str
    fps: float
    dispatched_intent: Optional[ActionIntent] = None
    study_active: bool = False
    study_state: str = "OFF"
    study_alert: Optional[str] = None
    study_result: Optional[StudyDetectionResult] = None



class GestureOSEngine:
    """Core GestureOS real-time execution engine."""

    def __init__(
        self,
        config: Optional[GestureOSConfig] = None,
        use_mock_controller: bool = False,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.config = config or GestureOSConfig()
        self.event_bus = event_bus or default_event_bus

        # Core State & Safety
        self.state_machine = GestureStateMachine(self.event_bus)
        self.activation_guard = ActivationGuard(
            self.state_machine,
            self.config.validation.activation_hold_sec,
            self.config.validation.allow_gesture_activation,
        )
        self.emergency_guard = EmergencyStopGuard(self.state_machine)

        # Platform Controller
        if use_mock_controller or self.config.camera.simulation_mode:
            self.controller: BaseOSController = MockOSController(
                self.config.cursor.screen_width, self.config.cursor.screen_height
            )
        else:
            self.controller = WindowsOSController()

        # Telemetry
        self.telemetry = TelemetryCollector(event_bus=self.event_bus)

        # Camera Engine
        self._init_camera()

        # Vision & Features
        self.detector = HandDetector(
            num_hands=2,
            min_detection_confidence=self.config.validation.min_confidence,
        )
        self.feature_extractor = FeatureExtractor()
        self.visualizer = DebugVisualizer()

        # Cursor & Gestures
        self.cursor_engine = CursorEngine(self.config.cursor, self.config.active_region)
        try:
            screen_w, screen_h = self.controller.get_screen_size()
            self.cursor_engine.set_screen_size(screen_w, screen_h)
            logger.info(f"Synchronized screen resolution: {screen_w}x{screen_h}")
        except Exception as e:
            logger.warning(f"Could not query screen size: {e}")
        self.static_detector = StaticGestureDetector(self.config.pinch)
        self.dynamic_detector = DynamicGestureDetector(
            self.config.validation, invert_x=self.config.cursor.invert_x
        )
        self.two_hand_coordinator = TwoHandCoordinator()
        self.ml_classifier = CustomMLGestureClassifier()
        self.temporal_validator = TemporalValidator(self.config.validation, self.config.cooldowns)

        # Modes & Dispatcher
        self.mode_manager = ModeManager(
            self.cursor_engine,
            self.config.pinch,
            self.config.default_mode,
            self.event_bus,
        )
        self.action_dispatcher = ActionDispatcher(
            self.controller, self.state_machine, event_bus=self.event_bus
        )

        # StudyGuard AI Meme Detector
        self.study_detector = StudyVisionDetector()
        self.study_audio_player = MemeAudioPlayer()
        self.study_state_machine = StudyStateMachine(audio_player=self.study_audio_player)
        self.enable_study_guard: bool = getattr(self.config, "enable_study_guard", False)

        # Threading
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.latest_output: Optional[PipelineFrameOutput] = None

    def set_study_guard_enabled(self, enabled: bool) -> None:
        """Toggles the StudyGuard meme detection pipeline on or off."""
        self.enable_study_guard = enabled
        self.config.enable_study_guard = enabled
        if not enabled:
            self.study_audio_player.stop()
        logger.info(f"Study Guard switched {'ON' if enabled else 'OFF'}")


    def _init_camera(self) -> None:
        if self.config.camera.simulation_mode:
            self.camera: BaseCamera = SimulationCamera(
                self.config.camera.width, self.config.camera.height, self.config.camera.fps
            )
        else:
            self.camera = OpenCVCamera(
                camera_index=self.config.camera.camera_index,
                width=self.config.camera.width,
                height=self.config.camera.height,
                fps=self.config.camera.fps,
                mirror=self.config.camera.mirror,
                auto_reconnect=self.config.camera.auto_reconnect,
                event_bus=self.event_bus,
            )

    def start(self) -> bool:
        """Starts real-time camera capture and gesture processing pipeline."""
        with self._lock:
            if self._is_running:
                return True

            logger.info("Starting GestureOS engine...")
            self.emergency_guard.start_keyboard_listener()
            cam_ok = self.camera.start()
            if not cam_ok and not self.config.camera.simulation_mode:
                logger.warning("Camera did not open immediately. Will wait for reconnect.")

            self._stop_event.clear()
            self._is_running = True
            self._worker_thread = threading.Thread(
                target=self._pipeline_worker, daemon=True, name="GestureOSPipelineWorker"
            )
            self._worker_thread.start()
            logger.info("GestureOS engine pipeline worker thread started.")
            return True

    def stop(self) -> None:
        """Gracefully halts pipeline and releases hardware resources."""
        with self._lock:
            if not self._is_running:
                return

            logger.info("Stopping GestureOS engine...")
            self._stop_event.set()
            self._is_running = False

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        self.camera.stop()
        self.emergency_guard.stop_keyboard_listener()
        self.detector.close()
        self.study_audio_player.stop()
        logger.info("GestureOS engine shut down cleanly.")

    def _pipeline_worker(self) -> None:
        target_frame_time = 1.0 / max(1, self.config.camera.fps)

        while not self._stop_event.is_set():
            t_start = time.time()

            try:
                output = self.step()
                if output is not None:
                    self.latest_output = output
            except Exception as e:
                logger.error(f"Error in pipeline frame step: {e}", exc_info=True)

            elapsed = time.time() - t_start
            sleep_time = max(0.001, target_frame_time - elapsed)
            time.sleep(sleep_time)

    def step(self, custom_frame: Optional[np.ndarray] = None) -> Optional[PipelineFrameOutput]:
        """Executes a single end-to-end iteration of the GestureOS pipeline."""
        t_frame_start = time.time()

        # 1. Camera Capture
        if custom_frame is not None:
            ret, frame = True, custom_frame
            cam_latency = 0.0
        else:
            t0 = time.time()
            ret, frame = self.camera.read_frame()
            cam_latency = (time.time() - t0) * 1000.0

        if not ret or frame is None:
            # Handle tracking loss / camera wait
            if self.state_machine.is_active and self.state_machine.current_state != GestureState.TRACKING_LOST:
                self.state_machine.transition_to(GestureState.TRACKING_LOST, "No camera frame")
            return None

        # 2. Vision & Hand Detection
        t1 = time.time()
        hands = self.detector.detect(frame)
        vision_latency = (time.time() - t1) * 1000.0

        dispatched_intent: Optional[ActionIntent] = None
        recognized_gesture_name = "none"
        confidence = 0.0
        primary_features: Optional[HandFeatures] = None

        t2 = time.time()
        now = time.time()

        if hands:
            # Auto-recover from TRACKING_LOST immediately when hand enters frame
            if self.state_machine.current_state == GestureState.TRACKING_LOST:
                self.state_machine.transition_to(GestureState.ACTIVE, "Hand restored in camera view")

            # Two-Hand Processing & Role Assignment
            hand_roles = self.two_hand_coordinator.assign_roles(hands)
            primary_hand = hand_roles["pointer_hand"] or hands[0]

            # Feature Extraction
            primary_features = self.feature_extractor.extract_features(primary_hand)

            # Static Gesture Recognition
            static_result = self.static_detector.detect(primary_hand, primary_features)

            # Dynamic Gesture Recognition (Trajectory buffer)
            index_pt = primary_hand.get(8).as_2d()
            dynamic_result = self.dynamic_detector.update(
                index_pt, primary_features, primary_hand, now
            )

            # Select Best Candidate (Simple Mode prioritizes clear static poses)
            if getattr(self.config, "simple_mode", True):
                if static_result.gesture in (
                    GestureType.THUMBS_UP,
                    GestureType.THUMBS_DOWN,
                    GestureType.PEACE,
                    GestureType.FIST,
                    GestureType.PINCH_INDEX,
                    GestureType.PINCH_MIDDLE,
                ):
                    chosen_result = static_result
                elif dynamic_result.gesture != GestureType.NONE:
                    chosen_result = dynamic_result
                else:
                    chosen_result = static_result
            else:
                chosen_result = dynamic_result if dynamic_result.gesture != GestureType.NONE else static_result

            # Check Custom ML Classifier if configured and deterministic is ambiguous
            if chosen_result.gesture == GestureType.NONE and self.ml_classifier.is_ready:
                ml_label, ml_conf = self.ml_classifier.predict(primary_hand, primary_features)
                if ml_label and ml_conf >= self.config.validation.min_confidence:
                    chosen_result = GestureRecognitionResult(
                        gesture=GestureType.CUSTOM_ML,
                        confidence=ml_conf,
                        hand_features=primary_features,
                        handedness=primary_hand.handedness,
                        raw_landmarks=primary_hand,
                        timestamp=now,
                        metadata={"custom_label": ml_label},
                    )

            # Check Two-Hand Emergency Stop (dual fists) or secondary gestures
            hand2 = None
            res2 = None
            if len(hands) >= 2:
                hand2 = hands[1]
                feat2 = self.feature_extractor.extract_features(hand2)
                res2 = self.static_detector.detect(hand2, feat2)
                dual_intent = self.two_hand_coordinator.process_hands(
                    [(primary_hand, primary_features, chosen_result), (hand2, feat2, res2)], now
                )
                if dual_intent and dual_intent.intent_type == IntentType.EMERGENCY_STOP_TRIGGER:
                    self.action_dispatcher.dispatch(dual_intent)

            # Temporal Validation
            validated_result = self.temporal_validator.validate(chosen_result)

            # Activation Guard
            is_allowed = self.activation_guard.evaluate(chosen_result)

            # Immediate gesture feedback for HUD and overlay
            if chosen_result.gesture != GestureType.NONE:
                recognized_gesture_name = chosen_result.gesture.value
                confidence = chosen_result.confidence
            elif validated_result is not None:
                recognized_gesture_name = validated_result.gesture.value
                confidence = validated_result.confidence

            if is_allowed:
                if self.mode_manager.current_mode_type == InteractionMode.MOUSE:
                    # In Mouse Mode, stream continuous hand tracking on every frame for fluid cursor movement and responsive pinch clicks
                    intent = self.mode_manager.process_gesture(
                        chosen_result,
                        primary_hand,
                        primary_features,
                        now,
                        secondary_result=res2,
                        secondary_landmarks=hand2,
                    )
                    if intent is not None:
                        dispatched = self.action_dispatcher.dispatch(intent)
                        if dispatched:
                            dispatched_intent = intent
                            if intent.intent_type != IntentType.MOUSE_MOVE:
                                self.telemetry.record_action_dispatched()
                else:
                    # Discrete interaction modes (Media, Browser, Window, Presentation) use temporally validated gestures
                    if validated_result is not None:
                        intent = self.mode_manager.process_gesture(
                            validated_result, primary_hand, primary_features, now
                        )
                        if intent is not None:
                            dispatched = self.action_dispatcher.dispatch(intent)
                            if dispatched:
                                dispatched_intent = intent
                                self.telemetry.record_action_dispatched()

        else:
            # No hands in frame -> Tracking Lost & Safe Cleanup
            self.cursor_engine.reset()
            active_mode = self.mode_manager.active_mode
            if hasattr(active_mode, "handle_hand_lost"):
                lost_intent = active_mode.handle_hand_lost(now)
                if lost_intent is not None:
                    self.action_dispatcher.dispatch(lost_intent)

            if self.state_machine.is_active and self.state_machine.current_state != GestureState.TRACKING_LOST:
                self.state_machine.transition_to(GestureState.TRACKING_LOST, "No hands detected in frame")

        gesture_latency = (time.time() - t2) * 1000.0

        # Record Telemetry
        self.telemetry.record_frame(cam_latency, vision_latency, gesture_latency, confidence)
        if recognized_gesture_name != "none":
            self.telemetry.record_gesture(recognized_gesture_name)

        snapshot = self.telemetry.get_snapshot()

        # StudyGuard Inference & Meme Evaluation
        study_res: Optional[StudyDetectionResult] = None
        study_st_str = "OFF"
        study_alert_str: Optional[str] = None
        if self.enable_study_guard:
            try:
                study_res = self.study_detector.detect(frame)
                st_enum = self.study_state_machine.update(study_res)
                study_st_str = st_enum.value
                study_alert_str = self.study_state_machine.recent_alert
            except Exception as e:
                logger.error(f"StudyGuard inference error: {e}")

        # Render Debug Overlay
        active_region = self.config.active_region if self.config.show_debug_overlay else None
        annotated = self.visualizer.render_overlay(
            frame,
            hands=hands,
            current_gesture=recognized_gesture_name,
            confidence=confidence,
            fps=snapshot.fps,
            state=self.state_machine.current_state.value,
            mode=self.mode_manager.current_mode_name,
            active_region=active_region,
            draw_landmarks=self.config.show_debug_overlay,
            study_result=study_res,
            study_alert=study_alert_str,
        )

        return PipelineFrameOutput(
            annotated_frame=annotated,
            raw_frame=frame,
            hands=hands,
            features=primary_features,
            gesture=recognized_gesture_name,
            confidence=confidence,
            state=self.state_machine.current_state.value,
            mode=self.mode_manager.current_mode_name,
            fps=snapshot.fps,
            dispatched_intent=dispatched_intent,
            study_active=self.enable_study_guard,
            study_state=study_st_str,
            study_alert=study_alert_str,
            study_result=study_res,
        )
