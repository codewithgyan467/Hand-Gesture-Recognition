"""Unit tests for landmark geometry, angle calculation, and scale normalization."""

import math
import pytest
from app.core.types import Point2D, Point3D, HandLandmarks, Handedness, HandLandmarkIndex
from app.vision.feature_extractor import calculate_angle_2d
from app.vision.normalizer import LandmarkNormalizer


def test_point2d_distance():
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(3.0, 4.0)
    assert math.isclose(p1.distance_to(p2), 5.0)


def test_point3d_distance():
    p1 = Point3D(0.0, 0.0, 0.0)
    p2 = Point3D(1.0, 2.0, 2.0)
    assert math.isclose(p1.distance_to(p2), 3.0)


def test_calculate_angle_right_angle():
    a = Point2D(0.0, 1.0)
    b = Point2D(0.0, 0.0)
    c = Point2D(1.0, 0.0)
    angle = calculate_angle_2d(a, b, c)
    assert math.isclose(angle, 90.0, abs_tol=1e-3)


def test_calculate_angle_straight_line():
    a = Point2D(-1.0, 0.0)
    b = Point2D(0.0, 0.0)
    c = Point2D(1.0, 0.0)
    angle = calculate_angle_2d(a, b, c)
    assert math.isclose(angle, 180.0, abs_tol=1e-3)


def test_landmark_normalizer_scale_invariance():
    # Construct a synthetic hand with known wrist and middle MCP
    pts1 = [Point3D(0.5, 0.5, 0.0) for _ in range(21)]
    pts1[HandLandmarkIndex.WRIST.value] = Point3D(0.5, 0.8, 0.0)
    pts1[HandLandmarkIndex.MIDDLE_FINGER_MCP.value] = Point3D(0.5, 0.5, 0.0)
    hand1 = HandLandmarks(landmarks=pts1)

    scale1 = LandmarkNormalizer.calculate_palm_scale(hand1)
    assert math.isclose(scale1, 0.3, abs_tol=1e-3)

    # Scale the hand coordinates by 2x (closer to camera)
    pts2 = [Point3D(p.x * 2, p.y * 2, p.z * 2) for p in pts1]
    hand2 = HandLandmarks(landmarks=pts2)
    scale2 = LandmarkNormalizer.calculate_palm_scale(hand2)
    assert math.isclose(scale2, 0.6, abs_tol=1e-3)

    # Inter-point distance normalized by scale should be identical!
    norm_dist1 = LandmarkNormalizer.calculate_normalized_distance(
        pts1[HandLandmarkIndex.WRIST.value], pts1[HandLandmarkIndex.MIDDLE_FINGER_MCP.value], scale1
    )
    norm_dist2 = LandmarkNormalizer.calculate_normalized_distance(
        pts2[HandLandmarkIndex.WRIST.value], pts2[HandLandmarkIndex.MIDDLE_FINGER_MCP.value], scale2
    )
    assert math.isclose(norm_dist1, norm_dist2, abs_tol=1e-4)


def test_active_region_mapping():
    # Center of active region (0.15 to 0.85) is 0.50 -> maps to 0.50
    pt_center = Point2D(0.50, 0.50)
    mapped = LandmarkNormalizer.map_to_active_region(pt_center, 0.15, 0.15, 0.85, 0.85)
    assert math.isclose(mapped.x, 0.50, abs_tol=1e-3)
    assert math.isclose(mapped.y, 0.50, abs_tol=1e-3)

    # Bottom-left of active region maps to 0.0
    pt_min = Point2D(0.15, 0.15)
    mapped_min = LandmarkNormalizer.map_to_active_region(pt_min, 0.15, 0.15, 0.85, 0.85)
    assert math.isclose(mapped_min.x, 0.0, abs_tol=1e-3)
    assert math.isclose(mapped_min.y, 0.0, abs_tol=1e-3)
