"""Exact deterministic axis freeze; true mask denotes injected positions."""
from __future__ import annotations
import numpy as np


def apply_axis_freeze(x_ref: np.ndarray, config: dict) -> tuple[np.ndarray, np.ndarray]:
    """One record [3,200] -> independent X_obs, assigned-site Z uint8."""
    if x_ref.shape != (3, 200) or x_ref.dtype != np.float64 or not np.isfinite(x_ref).all():
        raise ValueError("x_ref must be a finite float64 array of shape (3,200)")
    p = config["corruption"]
    axis = p["axis"]
    start = p["start_idx"]
    end = p["end_idx"]
    anchor = p["anchor_idx"]
    alpha = p["alpha"]
    x_obs = x_ref.copy()
    mask = np.zeros(x_ref.shape, dtype=np.uint8)
    if alpha > 0.0:
        mask[axis, start:end] = 1
        # IMPORTANT: read from the untouched reference, not from x_obs.
        x_obs[axis, start:end] = ((1.0 - alpha) * x_ref[axis, start:end]
                                  + alpha * x_ref[axis, anchor])
    # For alpha=0 do not write into the slice: exact array_equal is guaranteed.
    return x_obs, mask


def corrupt_both(x_ref: np.ndarray, config: dict) -> tuple[np.ndarray, np.ndarray]:
    if x_ref.shape != (2, 3, 200) or x_ref.dtype != np.float64:
        raise ValueError("Expected shape (2,3,200) float64")
    results = [apply_axis_freeze(x_ref[i], config) for i in range(2)]
    return np.stack([item[0] for item in results]), np.stack([item[1] for item in results])
