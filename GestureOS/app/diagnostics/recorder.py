"""Landmark recording and replay debugging engine for GestureOS.

Allows recording of normalized landmark sequences and replaying them for deterministic,
reproducible offline debugging without storing raw camera video frames.
"""

from __future__ import annotations
import json
import time
from typing import List, Dict, Any, Optional, Iterator, Tuple
from app.core.types import HandLandmarks, Point3D, Handedness, GestureType, GestureRecognitionResult
from app.diagnostics.logger import get_logger

logger = get_logger("recorder")


class LandmarkSessionRecorder:
    """Records landmark frames to JSONL stream for replay debugging."""

    def __init__(self, output_path: str) -> None:
        self.output_path = output_path
        self._is_recording = False
        self._file = None
        self._frame_count = 0

    def start(self) -> None:
        self._file = open(self.output_path, "w", encoding="utf-8")
        self._is_recording = True
        self._frame_count = 0
        logger.info(f"Landmark recording started: {self.output_path}")

    def record_frame(
        self,
        hands: List[HandLandmarks],
        recognized_gesture: GestureType = GestureType.NONE,
        confidence: float = 0.0,
    ) -> None:
        if not self._is_recording or self._file is None:
            return

        frame_data = {
            "timestamp": time.time(),
            "frame_idx": self._frame_count,
            "gesture": recognized_gesture.value if hasattr(recognized_gesture, "value") else str(recognized_gesture),
            "confidence": confidence,
            "hands": [
                {
                    "handedness": h.handedness.value,
                    "score": h.score,
                    "landmarks": [p.as_tuple() for p in h.landmarks],
                }
                for h in hands
            ],
        }

        self._file.write(json.dumps(frame_data) + "\n")
        self._file.flush()
        self._frame_count += 1

    def stop(self) -> None:
        if self._is_recording and self._file:
            self._file.close()
            self._file = None
            self._is_recording = False
            logger.info(f"Landmark recording stopped. Total frames recorded: {self._frame_count}")


class LandmarkSessionReplayer:
    """Reads a recorded JSONL session file and yields HandLandmarks sequences."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._frames: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        self._frames = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._frames.append(json.loads(line))
        logger.info(f"Loaded {len(self._frames)} frames from {self.file_path}")

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    def iter_frames(self) -> Iterator[Tuple[List[HandLandmarks], str, float]]:
        """Yields (hands, recorded_gesture, confidence)."""
        for item in self._frames:
            hands: List[HandLandmarks] = []
            for h_dict in item.get("hands", []):
                pts = [Point3D(x=p[0], y=p[1], z=p[2] if len(p) > 2 else 0.0) for p in h_dict["landmarks"]]
                handedness = Handedness(h_dict.get("handedness", "Unknown"))
                score = h_dict.get("score", 0.0)
                hands.append(HandLandmarks(landmarks=pts, handedness=handedness, score=score))

            yield hands, item.get("gesture", "none"), item.get("confidence", 0.0)
