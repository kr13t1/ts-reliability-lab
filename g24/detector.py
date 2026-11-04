"""G2.4 baseline A: offline maximal runs of exact float64 equality.

The detector API deliberately has no argument for ground truth, activity,
alpha, boundaries, timestamps or reference measurements.
"""
from __future__ import annotations

import numpy as np


def detect_constant_runs(observed_x: np.ndarray, L: int = 3) -> np.ndarray:
    """Return bool mask marking *all* samples in maximal exact runs >= L.

    Exact comparison is numerical float64 equality (+0 equals -0).  The
    returned mask is a retrospective offline prediction, not an injected mask.
    """
    if not isinstance(observed_x, np.ndarray) or observed_x.ndim != 1 or observed_x.dtype != np.float64:
        raise ValueError('observed_x must be a one-dimensional float64 ndarray')
    if observed_x.size < 1 or not np.isfinite(observed_x).all():
        raise ValueError('observed_x must be nonempty and finite')
    if type(L) is not int or L < 1:
        raise ValueError('L must be a positive Python int')
    n = observed_x.size
    result = np.zeros(n, dtype=np.bool_)
    if n < L:
        return result
    start = 0
    for end in range(1, n + 1):
        if end == n or observed_x[end] != observed_x[start]:
            if end - start >= L:
                result[start:end] = True
            start = end
    return result
