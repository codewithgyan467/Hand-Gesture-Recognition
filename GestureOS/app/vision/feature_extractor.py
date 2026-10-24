"""Feature extraction layer computing normalized geometric, kinematic, and angular features from hand landmarks."""

from __future__ import annotations
import math
import time
from typing import Dict, List, Tuple, Optional
from collections import deque
from app.core.types import (
    HandLandmarks,
    HandFeatures,
    Point2D,
    Point3D,
    HandLandmarkIndex,
    Handedness,
)
from app.vision.normalizer import LandmarkNormalizer


def calculate_angle_2d(a: Point3D | Point2D, b: Point3D | Point2D, c: Point3D | Point2D) -> float:
    """Calculates angle ABC (at vertex B) in degrees [0..180]."""
    v1_x = a.x - b.x
    v1_y = a.y - b.y
    v2_x = c.x - b.x
    v2_y = c.y - b.y

    dot = v1_x * v2_x + v1_y * v2_y
    mag1 = math.hypot(v1_x, v1_y)
    mag2 = math.hypot(v2_x, v2_y)

    if mag1 * mag2 < 1e-7:
        return 0.0

    cosine = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cosine))


class FeatureExtractor:
    """Calculates rich geometric, angular, and kinematic features from hand landmarks."""

    def __init__(self, history_len: int = 15) -> None:
        self.history_len = history_len
        self._position_history: deque = deque(maxlen=history_len) # (timestamp, Point2D)

    def extract_features(self, landmarks: HandLandmarks) -> HandFeatures:
        palm_scale = LandmarkNormalizer.calculate_palm_scale(landmarks)
        palm_center = LandmarkNormalizer.calculate_palm_center(landmarks)
        bounding_box = LandmarkNormalizer.get_bounding_box(landmarks)

        # Joint points
        wrist = landmarks.get(HandLandmarkIndex.WRIST)
        thumb_cmc = landmarks.get(HandLandmarkIndex.THUMB_CMC)
        thumb_mcp = landmarks.get(HandLandmarkIndex.THUMB_MCP)
        thumb_ip = landmarks.get(HandLandmarkIndex.THUMB_IP)
        thumb_tip = landmarks.get(HandLandmarkIndex.THUMB_TIP)

        index_mcp = landmarks.get(HandLandmarkIndex.INDEX_FINGER_MCP)
        index_pip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_PIP)
        index_dip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_DIP)
        index_tip = landmarks.get(HandLandmarkIndex.INDEX_FINGER_TIP)

        middle_mcp = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_MCP)
        middle_pip = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_PIP)
        middle_dip = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_DIP)
        middle_tip = landmarks.get(HandLandmarkIndex.MIDDLE_FINGER_TIP)

        ring_mcp = landmarks.get(HandLandmarkIndex.RING_FINGER_MCP)
        ring_pip = landmarks.get(HandLandmarkIndex.RING_FINGER_PIP)
        ring_dip = landmarks.get(HandLandmarkIndex.RING_FINGER_DIP)
        ring_tip = landmarks.get(HandLandmarkIndex.RING_FINGER_TIP)

        pinky_mcp = landmarks.get(HandLandmarkIndex.PINKY_MCP)
        pinky_pip = landmarks.get(HandLandmarkIndex.PINKY_PIP)
        pinky_dip = landmarks.get(HandLandmarkIndex.PINKY_DIP)
        pinky_tip = landmarks.get(HandLandmarkIndex.PINKY_TIP)

        # 1. Angles at PIP/IP joints
        thumb_angle = calculate_angle_2d(thumb_mcp, thumb_ip, thumb_tip)
        index_angle = calculate_angle_2d(index_mcp, index_pip, index_tip)
        middle_angle = calculate_angle_2d(middle_mcp, middle_pip, middle_tip)
        ring_angle = calculate_angle_2d(ring_mcp, ring_pip, ring_tip)
        pinky_angle = calculate_angle_2d(pinky_mcp, pinky_pip, pinky_tip)

        curl_angles = {
            "thumb": thumb_angle,
            "index": index_angle,
            "middle": middle_angle,
            "ring": ring_angle,
            "pinky": pinky_angle,
        }

        # 2. Extension determination (distance from wrist & joint angle)
        dist_wrist_thumb = wrist.distance_to(thumb_tip)
        dist_wrist_index = wrist.distance_to(index_tip)
        dist_wrist_middle = wrist.distance_to(middle_tip)
        dist_wrist_ring = wrist.distance_to(ring_tip)
        dist_wrist_pinky = wrist.distance_to(pinky_tip)

        # Index/Middle/Ring/Pinky extended if tip is higher/further than PIP and angle > 140
        is_index_ext = (index_angle > 140.0) and (dist_wrist_index > wrist.distance_to(index_pip))
        is_middle_ext = (middle_angle > 140.0) and (dist_wrist_middle > wrist.distance_to(middle_pip))
        is_ring_ext = (ring_angle > 140.0) and (dist_wrist_ring > wrist.distance_to(ring_pip))
        is_pinky_ext = (pinky_angle > 140.0) and (dist_wrist_pinky > wrist.distance_to(pinky_pip))

        # Thumb extension: distance from index MCP and angle
        thumb_span = LandmarkNormalizer.calculate_normalized_distance(thumb_tip, index_mcp, palm_scale)
        is_thumb_ext = (thumb_angle > 145.0) and (thumb_span > 0.45)

        finger_extended = {
            "thumb": is_thumb_ext,
            "index": is_index_ext,
            "middle": is_middle_ext,
            "ring": is_ring_ext,
            "pinky": is_pinky_ext,
        }

        # 3. Inter-finger normalized distances
        thumb_index_dist = LandmarkNormalizer.calculate_normalized_distance(thumb_tip, index_tip, palm_scale)
        thumb_middle_dist = LandmarkNormalizer.calculate_normalized_distance(thumb_tip, middle_tip, palm_scale)

        # 4. Velocity tracking
        now = time.time()
        self._position_history.append((now, index_tip.as_2d()))
        velocity = self._calculate_velocity()

        # 5. Palm tilt
        palm_tilt = math.degrees(math.atan2(index_mcp.y - wrist.y, index_mcp.x - wrist.x))

        return HandFeatures(
            palm_center=palm_center,
            hand_scale=palm_scale,
            finger_extended=finger_extended,
            finger_curl_angles=curl_angles,
            thumb_index_dist=thumb_index_dist,
            thumb_middle_dist=thumb_middle_dist,
            bounding_box=bounding_box,
            velocity=velocity,
            palm_tilt=palm_tilt,
        )

    def _calculate_velocity(self) -> Point2D:
        if len(self._position_history) < 2:
            return Point2D(0.0, 0.0)

        t_old, pos_old = self._position_history[0]
        t_new, pos_new = self._position_history[-1]
        dt = t_new - t_old
        if dt < 1e-4:
            return Point2D(0.0, 0.0)

        vx = (pos_new.x - pos_old.x) / dt
        vy = (pos_new.y - pos_old.y) / dt
        return Point2D(vx, vy)

    def reset(self) -> None:
        self._position_history.clear()
