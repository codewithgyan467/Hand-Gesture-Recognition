"""Air drawing mode maintaining a virtual canvas with strokes, undo/redo, eraser, and export."""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from app.modes.base_mode import BaseMode
from app.core.types import (
    InteractionMode,
    GestureType,
    GestureRecognitionResult,
    HandLandmarks,
    HandFeatures,
    ActionIntent,
    IntentType,
    HandLandmarkIndex,
    Point2D,
)
from app.cursor.cursor_engine import CursorEngine


@dataclass
class Stroke:
    points: List[Tuple[int, int]] = field(default_factory=list)
    color: Tuple[int, int, int] = (0, 255, 255) # BGR Yellow default
    width: int = 4
    is_eraser: bool = False


class DrawingMode(BaseMode):
    """Virtual air canvas drawing mode."""

    def __init__(self, cursor_engine: CursorEngine, canvas_width: int = 640, canvas_height: int = 480) -> None:
        super().__init__(InteractionMode.DRAWING, cursor_engine)
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.strokes: List[Stroke] = []
        self._redo_stack: List[Stroke] = []
        self._current_stroke: Optional[Stroke] = None
        self.brush_color: Tuple[int, int, int] = (0, 255, 255) # Neon yellow BGR
        self.brush_width: int = 4
        self.is_eraser: bool = False
        self._last_undo_time: float = 0.0
        self._last_tool_toggle_time: float = 0.0

    def process_gesture(
        self,
        gesture_result: GestureRecognitionResult,
        landmarks: HandLandmarks,
        features: HandFeatures,
        timestamp: float,
    ) -> Optional[ActionIntent]:
        g = gesture_result.gesture

        # 1. Clear Canvas (Wave gesture)
        if g == GestureType.WAVE:
            self.clear_canvas()
            return ActionIntent(
                intent_type=IntentType.DRAW_CLEAR,
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )

        # 2. Simple Undo (👍) & Redo (👎)
        if g == GestureType.THUMBS_UP:
            if timestamp - self._last_undo_time >= 0.35:
                self._last_undo_time = timestamp
                success = self.undo()
                return ActionIntent(
                    intent_type=IntentType.DRAW_UNDO,
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    params={"success": success},
                    source_gesture=GestureType.THUMBS_UP,
                )
            return None

        if g == GestureType.THUMBS_DOWN:
            if timestamp - self._last_undo_time >= 0.35:
                self._last_undo_time = timestamp
                success = self.redo()
                return ActionIntent(
                    intent_type=IntentType.DRAW_REDO,
                    confidence=gesture_result.confidence,
                    timestamp=timestamp,
                    params={"success": success},
                    source_gesture=GestureType.THUMBS_DOWN,
                )
            return None

        # 3. Tool Switch: Brush vs Eraser (✌ Peace gesture)
        if g == GestureType.PEACE:
            if timestamp - self._last_tool_toggle_time >= 0.40:
                self._last_tool_toggle_time = timestamp
                self.is_eraser = not self.is_eraser
            return None

        # 4. Pause Drawing (Fist)
        if g == GestureType.FIST:
            self._finish_stroke()
            return None

        # 5. Air Draw (Index Pointer or Open Palm)
        if g in (GestureType.POINTER, GestureType.OPEN_PALM):
            index_tip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP)
            px = int(index_tip.x * self.canvas_width)
            py = int(index_tip.y * self.canvas_height)

            if self._current_stroke is None:
                self._current_stroke = Stroke(
                    color=(0, 0, 0) if self.is_eraser else self.brush_color,
                    width=self.brush_width * (3 if self.is_eraser else 1),
                    is_eraser=self.is_eraser,
                )
                self.strokes.append(self._current_stroke)
                self._redo_stack.clear()

            self._current_stroke.points.append((px, py))
            return ActionIntent(
                intent_type=IntentType.DRAW_STROKE,
                params={"x": px, "y": py},
                confidence=gesture_result.confidence,
                timestamp=timestamp,
            )
        else:
            self._finish_stroke()

        return None

    def _finish_stroke(self) -> None:
        self._current_stroke = None

    def undo(self) -> bool:
        if self.strokes:
            stroke = self.strokes.pop()
            self._redo_stack.append(stroke)
            return True
        return False

    def redo(self) -> bool:
        if self._redo_stack:
            stroke = self._redo_stack.pop()
            self.strokes.append(stroke)
            return True
        return False

    def clear_canvas(self) -> None:
        self.strokes.clear()
        self._redo_stack.clear()
        self._current_stroke = None

    def render_canvas(self, background: Optional[np.ndarray] = None) -> np.ndarray:
        """Renders drawing strokes onto background frame or transparent canvas."""
        if background is not None:
            canvas = background
        else:
            canvas = np.zeros((self.canvas_height, self.canvas_width, 3), dtype=np.uint8)

        for stroke in self.strokes:
            if len(stroke.points) < 2:
                if len(stroke.points) == 1:
                    cv2.circle(canvas, stroke.points[0], stroke.width // 2, stroke.color, -1, cv2.LINE_AA)
                continue

            for i in range(1, len(stroke.points)):
                cv2.line(canvas, stroke.points[i - 1], stroke.points[i], stroke.color, stroke.width, cv2.LINE_AA)

        return canvas

    def export_canvas(self, output_path: str) -> bool:
        canvas = self.render_canvas()
        return cv2.imwrite(output_path, canvas)

    def export_svg(self, output_path: str) -> bool:
        """Exports all strokes as vector SVG paths."""
        try:
            svg_lines = [
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.canvas_width} {self.canvas_height}" width="{self.canvas_width}" height="{self.canvas_height}">',
                '<rect width="100%" height="100%" fill="#1a1d20"/>',
            ]
            for stroke in self.strokes:
                if not stroke.points:
                    continue
                b, g, r = stroke.color
                hex_color = f"#{r:02x}{g:02x}{b:02x}" if not stroke.is_eraser else "#1a1d20"
                if len(stroke.points) == 1:
                    px, py = stroke.points[0]
                    svg_lines.append(f'<circle cx="{px}" cy="{py}" r="{max(1, stroke.width // 2)}" fill="{hex_color}"/>')
                else:
                    path_d = f"M {stroke.points[0][0]} {stroke.points[0][1]} "
                    for pt in stroke.points[1:]:
                        path_d += f"L {pt[0]} {pt[1]} "
                    svg_lines.append(f'<path d="{path_d}" stroke="{hex_color}" stroke-width="{stroke.width}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
            svg_lines.append('</svg>')
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))
            return True
        except Exception:
            return False

    def on_exit(self) -> None:
        self._finish_stroke()
