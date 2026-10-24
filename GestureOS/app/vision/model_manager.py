"""Lazy-loading, lifecycle-managed ModelManager for GestureOS & StudyGuard."""

from __future__ import annotations
import gc
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.resources import get_resource_manager, ResourceStatus
from app.diagnostics.logger import get_logger

logger = get_logger("model_manager")


class ModelManager:
    """Manages the lifecycle, lazy instantiation, validation, and unloading of ML models."""

    def __init__(self) -> None:
        self.rm = get_resource_manager()
        self._lock = threading.Lock()
        self._study_detector: Optional[Any] = None

    def validate_models(self) -> Dict[str, ResourceStatus]:
        """Validates existence and file size of all required neural network models."""
        return self.rm.validate_all_models()

    def is_study_models_loaded(self) -> bool:
        """Checks if StudyGuard models are currently consuming memory."""
        with self._lock:
            return self._study_detector is not None

    @property
    def is_study_detector_loaded(self) -> bool:
        return self.is_study_models_loaded()

    def get_or_load_study_detector(
        self,
        min_object_confidence: float = 0.28,
        min_face_confidence: float = 0.40,
    ) -> Optional[Any]:
        """Lazily loads StudyGuard detector models only when StudyGuard is active."""
        with self._lock:
            if self._study_detector is not None:
                return self._study_detector

            # Verify model files exist before loading
            statuses = self.validate_models()
            obj_st = statuses.get("efficientdet_lite0.tflite")
            face_st = statuses.get("blaze_face_short_range.tflite")

            if obj_st and not obj_st.is_valid:
                logger.error(f"Cannot load StudyGuard: {obj_st.error_message}")
                return None
            if face_st and not face_st.is_valid:
                logger.error(f"Cannot load StudyGuard: {face_st.error_message}")
                return None

            try:
                from app.vision.study_detector import StudyVisionDetector
                logger.info("Lazily loading StudyGuard neural models into memory...")
                self._study_detector = StudyVisionDetector(
                    min_object_confidence=min_object_confidence,
                    min_face_confidence=min_face_confidence,
                )
                logger.info("StudyGuard models loaded successfully.")
                return self._study_detector
            except Exception as e:
                logger.error(f"Failed to load StudyGuard detector models: {e}", exc_info=True)
                self._study_detector = None
                return None

    def unload_study_detector(self) -> None:
        """Releases StudyGuard neural network models from memory when StudyGuard is toggled OFF."""
        with self._lock:
            if self._study_detector is not None:
                logger.info("Unloading StudyGuard models to reclaim memory and CPU cycles...")
                try:
                    if hasattr(self._study_detector, "close"):
                        self._study_detector.close()
                except Exception as e:
                    logger.warning(f"Error during StudyVisionDetector close: {e}")
                self._study_detector = None
                gc.collect()
                logger.info("StudyGuard models unloaded.")

    def close(self) -> None:
        """Releases all managed model instances."""
        self.unload_study_detector()

    def close_all(self) -> None:
        """Alias for close()."""
        self.close()
