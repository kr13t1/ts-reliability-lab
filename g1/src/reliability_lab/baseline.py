"""Single fixed activity classifier: per-axis centered global RMS."""
from __future__ import annotations
import numpy as np


def rms_score(x: np.ndarray) -> float:
    if x.shape != (3, 200):
        raise ValueError("Expected a single (3,200) record")
    centered = x - np.mean(x, axis=1, keepdims=True)
    return float(np.sqrt(np.mean(centered ** 2)))


def predict_activity(x: np.ndarray, *, threshold_m_s2: float = 0.20) -> int:
    """Threshold is fixed by contract; no fit, training, or optimization."""
    if threshold_m_s2 != 0.20:
        raise ValueError("The G1 threshold is fixed at 0.20 m/s^2")
    return int(rms_score(x) >= threshold_m_s2)
