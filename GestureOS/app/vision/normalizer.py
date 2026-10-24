"""Coordinate and scale normalization layer for invariant hand tracking across users and cameras."""

from __future__ import annotations
import math
from typing import Tuple, List
from app.core.types import HandLandmarks, Point2D, Point3D, HandLandmarkIndex


class LandmarkNormalizer:
    """Normalizes hand landmarks and distances for resolution and scale independence."""

    @staticmethod
    def calculate_palm_scale(landmarks: HandLandmarks) -> float:
        """Calculates scale-invariant palm reference distance using rigid palm landmarks.
        
        Uses distance between WRIST (0) and MIDDLE_FINGER_MCP (9). Metacarpal bones do not bend,
        making this a reliable measure of hand distance and user hand size.
        """
        wrist = landmarks.get(HandLandmarkIndex.WRIST)
        middle_mcp = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_MCP)
        scale = math.hypot(middle_mcp.x - wrist.x, middle_mcp.y - wrist.y)
        return max(0.01, scale)

    @staticmethod
    def calculate_palm_center(landmarks: HandLandmarks) -> Point2D:
        """Calculates centroid of the palm using WRIST, INDEX_MCP, and PINKY_MCP."""
        wrist = landmarks.get(HandLandmarkIndex.WRIST)
        index_mcp = landmarks.get(HandLandmarkIndex.INDEX_FINGER_MCP)
        pinky_mcp = landmarks.get(HandLandmarkIndex.PINKY_MCP)

        cx = (wrist.x + index_mcp.x + pinky_mcp.x) / 3.0
        cy = (wrist.y + index_mcp.y + pinky_mcp.y) / 3.0
        return Point2D(cx, cy)

    @staticmethod
    def map_to_active_region(
        point: Point2D,
        x_min: float = 0.15,
        y_min: float = 0.15,
        x_max: float = 0.85,
        y_max: float = 0.85,
    ) -> Point2D:
        """Maps camera normalized point [x_min..x_max, y_min..y_max] to normalized screen [0.0, 1.0]."""
        clamped_x = max(x_min, min(x_max, point.x))
        clamped_y = max(y_min, min(y_max, point.y))

        span_x = max(0.01, x_max - x_min)
        span_y = max(0.01, y_max - y_min)

        norm_x = (clamped_x - x_min) / span_x
        norm_y = (clamped_y - y_min) / span_y

        return Point2D(norm_x, norm_y)

    @staticmethod
    def calculate_normalized_distance(p1: Point3D, p2: Point3D, palm_scale: float) -> float:
        """Computes Euclidean distance between two points normalized by palm scale."""
        raw_dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
        return raw_dist / max(0.001, palm_scale)

    @staticmethod
    def get_bounding_box(landmarks: HandLandmarks) -> Tuple[float, float, float, float]:
        """Returns (min_x, min_y, max_x, max_y) normalized bounding box."""
        xs = [p.x for p in landmarks.landmarks]
        ys = [p.y for p in landmarks.landmarks]
        return (min(xs), min(ys), max(xs), max(ys))
