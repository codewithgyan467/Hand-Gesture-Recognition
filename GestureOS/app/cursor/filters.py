"""Jitter reduction and temporal smoothing filters: One Euro Filter, EMA, and Kalman Filter."""

from __future__ import annotations
import math
import time
from typing import Tuple, Optional


class LowPassFilter:
    """Standard first-order low-pass filter."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self.last_val: Optional[float] = None

    def filter(self, value: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.last_val is None:
            self.last_val = value
            return value
        filtered = self.alpha * value + (1.0 - self.alpha) * self.last_val
        self.last_val = filtered
        return filtered

    def reset(self) -> None:
        self.last_val = None


class OneEuroFilter1D:
    """1D One Euro Filter for adaptive jitter-filtering at low speeds and zero-lag at high speeds."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.x_filt = LowPassFilter()
        self.dx_filt = LowPassFilter()
        self.last_time: Optional[float] = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(1e-4, cutoff))
        return 1.0 / (1.0 + tau / max(1e-4, dt))

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        if timestamp is None:
            timestamp = time.time()

        if self.last_time is None:
            self.last_time = timestamp
            return self.x_filt.filter(x)

        dt = timestamp - self.last_time
        if dt <= 1e-5:
            dt = 1e-4
        self.last_time = timestamp

        # Estimate derivative of the signal
        prev_x = self.x_filt.last_val if self.x_filt.last_val is not None else x
        dx = (x - prev_x) / dt
        edx = self.dx_filt.filter(dx, self._alpha(self.d_cutoff, dt))

        # Dynamic cutoff frequency based on velocity
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filt.filter(x, self._alpha(cutoff, dt))

    def reset(self) -> None:
        self.x_filt.reset()
        self.dx_filt.reset()
        self.last_time = None


class OneEuroFilter2D:
    """2D One Euro Filter coordinate filter."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self.filter_x = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.filter_y = OneEuroFilter1D(min_cutoff, beta, d_cutoff)

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.time()
        fx = self.filter_x.filter(x, timestamp)
        fy = self.filter_y.filter(y, timestamp)
        return (fx, fy)

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()


class ExponentialMovingAverage2D:
    """Exponential Moving Average (EMA) coordinate filter."""

    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = alpha
        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.last_x is None or self.last_y is None:
            self.last_x = x
            self.last_y = y
            return (x, y)

        self.last_x = self.alpha * x + (1.0 - self.alpha) * self.last_x
        self.last_y = self.alpha * y + (1.0 - self.alpha) * self.last_y
        return (self.last_x, self.last_y)

    def reset(self) -> None:
        self.last_x = None
        self.last_y = None


class KalmanFilter2D:
    """Simple 2D constant velocity linear Kalman Filter."""

    def __init__(self, process_noise: float = 1e-2, measurement_noise: float = 1e-1) -> None:
        self.q = process_noise
        self.r = measurement_noise
        self.x = 0.0
        self.y = 0.0
        self.p_x = 1.0
        self.p_y = 1.0
        self.is_initialized = False

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if not self.is_initialized:
            self.x = x
            self.y = y
            self.is_initialized = True
            return (x, y)

        # Predict
        self.p_x += self.q
        self.p_y += self.q

        # Update
        k_x = self.p_x / (self.p_x + self.r)
        k_y = self.p_y / (self.p_y + self.r)

        self.x += k_x * (x - self.x)
        self.y += k_y * (y - self.y)

        self.p_x *= (1.0 - k_x)
        self.p_y *= (1.0 - k_y)

        return (self.x, self.y)

    def reset(self) -> None:
        self.is_initialized = False
